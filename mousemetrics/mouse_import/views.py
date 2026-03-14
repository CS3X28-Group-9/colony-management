from typing import Any, Dict, Callable, TypeVar

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import ColumnMappingForm, MouseImportForm, MouseImportSheetRangeForm
from .models import MouseImport
from .services.importer import ImportOptions, Importer
from .services.io import list_sheet_names, read_range
from .services.validators import cell_range_boundaries, normalise_cell_range

from .services.mapping_ai import suggest_mapping_for_dataframe, record_mapping_examples
from .services.mapping_train import maybe_train_mapping_model
from django.conf import settings

# Type-checker-friendly aliases for decorators
F = TypeVar("F", bound=Callable[..., HttpResponseBase])
login_required_decorator: Callable[[F], F] = login_required  # type: ignore[assignment]
require_get_decorator: Callable[[F], F] = require_GET  # type: ignore[assignment]

PREVIEW_ROW_LIMIT = settings.PREVIEW_ROW_LIMIT
TRAIN_ON_SAVE = settings.TRAIN_ON_SAVE
TRAIN_MIN_NEW = settings.TRAIN_MIN_NEW

# Second-step live preview limits (kept intentionally small)
RANGE_PREVIEW_ROW_LIMIT = getattr(settings, "RANGE_PREVIEW_ROW_LIMIT", 10)
RANGE_PREVIEW_COL_LIMIT = getattr(settings, "RANGE_PREVIEW_COL_LIMIT", 12)
RANGE_PREVIEW_CELL_CHAR_LIMIT = getattr(settings, "RANGE_PREVIEW_CELL_CHAR_LIMIT", 120)


def _df_session_key(import_pk: int) -> str:
    return f"import_df_{import_pk}"


def _map_session_key(import_pk: int) -> str:
    return f"import_map_{import_pk}"


@login_required_decorator
def import_form(request: HttpRequest) -> HttpResponse:
    form = MouseImportForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        import_obj = form.save(commit=False)
        import_obj.uploaded_by = request.user

        uploaded_file = request.FILES.get("file")
        if uploaded_file is not None:
            import_obj.original_filename = uploaded_file.name

        # Sheet/range are chosen in step 2.
        import_obj.sheet_name = ""
        import_obj.cell_range = ""

        import_obj.save()
        messages.success(request, "Upload saved. Choose sheet and range…")
        return redirect("mouse_import:import_select_range", id=import_obj.id)

    return render(
        request, "mouse_import/import_form.html", {"form": form, "user": request.user}
    )


@login_required_decorator
def import_select_range(request: HttpRequest, id: int) -> HttpResponse:
    """Step 2: capture sheet_name + cell_range, with live preview."""

    import_obj = get_object_or_404(MouseImport, id=id)

    try:
        sheets = list_sheet_names(
            import_obj.file.path, original_filename=import_obj.original_filename
        )
    except Exception as exc:  # pragma: no cover - user-facing
        sheets = []
        messages.error(request, f"Could not read workbook sheets: {exc}")

    form = MouseImportSheetRangeForm(
        request.POST or None, instance=import_obj, sheet_choices=sheets
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        # Range/sheet changes invalidate any cached preview + mapping selections.
        request.session.pop(_df_session_key(import_obj.id), None)
        request.session.pop(_map_session_key(import_obj.id), None)

        messages.success(request, "Range saved. Continue to mapping…")
        return redirect("mouse_import:import_preview", id=import_obj.id)

    context: Dict[str, Any] = {
        "import_obj": import_obj,
        "range_form": form,
        "sheet_names": sheets,
    }
    return render(request, "mouse_import/import_preview.html", context)


@login_required_decorator
@require_get_decorator
def import_range_preview(request: HttpRequest, id: int) -> JsonResponse:
    """AJAX endpoint used by the sheet/range step to preview a valid range."""

    import_obj = get_object_or_404(MouseImport, id=id)

    sheet = (request.GET.get("sheet") or "").strip() or None
    cell_range_raw = (request.GET.get("cell_range") or "").strip()

    try:
        cell_range = normalise_cell_range(cell_range_raw)
        boundaries = cell_range_boundaries(cell_range)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    # Validate sheet name against workbook sheet names when applicable.
    try:
        sheets = list_sheet_names(
            import_obj.file.path, original_filename=import_obj.original_filename
        )
    except Exception:
        sheets = []
    if sheet and sheets and sheet not in sheets:
        return JsonResponse({"error": "Select a valid sheet."}, status=400)

    try:
        df = read_range(
            import_obj.file.path,
            sheet,
            cell_range,
            original_filename=import_obj.original_filename,
            limit=RANGE_PREVIEW_ROW_LIMIT,
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if df.empty:
        return JsonResponse(
            {"error": "Selected range does not contain any data."}, status=400
        )

    # Limit columns for safety/UX
    truncated_columns = False
    if len(df.columns) > RANGE_PREVIEW_COL_LIMIT:
        df = df.iloc[:, :RANGE_PREVIEW_COL_LIMIT]
        truncated_columns = True

    def _truncate(v: Any) -> str:
        if v is None:
            return ""
        s = str(v)
        if len(s) <= RANGE_PREVIEW_CELL_CHAR_LIMIT:
            return s
        return s[: max(0, RANGE_PREVIEW_CELL_CHAR_LIMIT - 1)] + "…"

    columns = [str(c) for c in df.columns]
    rows = [
        [_truncate(v) for v in row] for row in df.itertuples(index=False, name=None)
    ]

    # Range includes header row; data rows are everything after that.
    data_rows_in_range = max(
        0, int(boundaries["last_row"]) - int(boundaries["first_row"])
    )
    truncated_rows = data_rows_in_range > RANGE_PREVIEW_ROW_LIMIT

    return JsonResponse(
        {
            "boundaries": boundaries,
            "columns": columns,
            "rows": rows,
            "truncated": {
                "columns": truncated_columns,
                "rows": truncated_rows,
            },
        }
    )


@login_required_decorator
def import_preview(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)

    # Enforce step ordering: must pick a range first.
    if not (import_obj.cell_range or "").strip():
        return redirect("mouse_import:import_select_range", id=import_obj.id)

    df_key = _df_session_key(import_obj.id)
    map_key = _map_session_key(import_obj.id)

    if df_key in request.session:
        raw_df = request.session[df_key]
        df = pd.read_json(raw_df, orient="records")
    else:
        try:
            df = read_range(
                import_obj.file.path,
                import_obj.sheet_name,
                import_obj.cell_range,
                original_filename=import_obj.original_filename,
                limit=PREVIEW_ROW_LIMIT,
            )
            request.session[df_key] = df.to_json(orient="records")
        except Exception as exc:  # pragma: no cover - reported to the user
            messages.error(
                request, f"Error reading file range: {exc}", extra_tags="range_error"
            )
            return redirect("mouse_import:import_select_range", id=import_obj.id)

    if df.empty:
        messages.error(
            request,
            "Selected range does not contain any data.",
            extra_tags="range_error",
        )
        return redirect("mouse_import:import_select_range", id=import_obj.id)

    columns = list(df.columns)
    import_obj.row_count = len(df)  # TODO
    import_obj.save(update_fields=["row_count"])

    saved_initial, saved_fixed, saved_mapping = request.session.get(map_key) or (
        None,
        None,
        None,
    )

    suggested_initial = None
    suggestions_debug = None
    if saved_initial is None:
        suggested_initial, suggestions_debug = suggest_mapping_for_dataframe(
            df, import_obj.project
        )

    if request.method == "POST":
        form = ColumnMappingForm(
            request.POST, columns=columns, project=import_obj.project
        )
        if form.is_valid():
            initial, fixed, mapping = form.selected_mapping()
            request.session[map_key] = (initial, fixed, mapping)

            # Record training data from *explicit* mappings only
            created_n = record_mapping_examples(
                import_obj, df, user=request.user, mapping=mapping
            )

            # Trigger training (simple: on-save check) if enabled
            if TRAIN_ON_SAVE and created_n > 0:
                outcome = maybe_train_mapping_model(min_new_examples=TRAIN_MIN_NEW)

                # Keep low-noise unless training occurred/failure:
                msg = outcome.user_message()
                if msg:
                    messages.info(request, msg)

            messages.success(request, "Column mapping saved.")
            return redirect("mouse_import:import_preview", id=import_obj.id)
    else:
        form = ColumnMappingForm(
            columns=columns,
            initial=saved_initial or suggested_initial,
            project=import_obj.project,
        )

    preview_rows = df.to_dict(orient="records")

    context: Dict[str, Any] = {
        "import_obj": import_obj,
        "columns": columns,
        "rows": preview_rows,
        "form": form,
        "saved_mapping": saved_mapping,
        "saved_fixed": saved_fixed,
        "suggestions": suggestions_debug,
    }
    return render(request, "mouse_import/import_preview.html", context)


@login_required_decorator
def import_commit(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)

    if not (import_obj.cell_range or "").strip():
        return redirect("mouse_import:import_select_range", id=import_obj.id)
    df_key = _df_session_key(import_obj.id)
    map_key = _map_session_key(import_obj.id)

    _, fixed, mapping = request.session.get(map_key) or (None, None, None)

    if mapping is None or fixed is None:
        messages.error(
            request,
            "Missing preview data or column mapping. Please re-upload and save the mapping.",
        )
        return redirect("mouse_import:import_preview", id=import_obj.id)

    df = read_range(
        import_obj.file.path,
        import_obj.sheet_name,
        import_obj.cell_range,
        original_filename=import_obj.original_filename,
        mapping=mapping,
    )
    importer = Importer(
        ImportOptions(
            project_id=import_obj.project.id,
            sheet=import_obj.sheet_name or "",
            range_expr=import_obj.cell_range,
        )
    )
    created_ids, updated_ids, errors = importer.run(df, fixed, mapping)

    import_obj.committed = True
    import_obj.row_count = len(df)
    import_obj.error_log = "\n".join(errors)[:5000] if errors else ""

    import_obj.file.delete()

    import_obj.save(update_fields=["committed", "row_count", "error_log"])

    request.session.pop(df_key, None)
    request.session.pop(map_key, None)

    context = {
        "import_obj": import_obj,
        "created": len(created_ids),
        "updated": len(updated_ids),
        "errors": errors,
    }
    return render(request, "mouse_import/import_result.html", context)
