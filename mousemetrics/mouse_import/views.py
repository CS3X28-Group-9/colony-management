from typing import Any, Dict

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ColumnMappingForm, MouseImportForm
from .models import MouseImport
from .services.importer import ImportOptions, Importer
from .services.io import read_range

from .services.mapping_ai import suggest_mapping_for_dataframe, record_mapping_examples
from .services.mapping_train import maybe_train_mapping_model
from django.conf import settings

PREVIEW_ROW_LIMIT = settings.PREVIEW_ROW_LIMIT
TRAIN_ON_SAVE = settings.TRAIN_ON_SAVE
TRAIN_MIN_NEW = settings.TRAIN_MIN_NEW


def _df_session_key(import_pk: int) -> str:
    return f"import_df_{import_pk}"


def _map_session_key(import_pk: int) -> str:
    return f"import_map_{import_pk}"


@login_required
def import_form(request: HttpRequest) -> HttpResponse:
    form = MouseImportForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        import_obj = form.save(commit=False)
        import_obj.uploaded_by = request.user

        uploaded_file = request.FILES.get("file")
        if uploaded_file is not None:
            import_obj.original_filename = uploaded_file.name

        import_obj.save()
        messages.success(request, "Upload saved. Redirecting to preview…")
        return redirect("mouse_import:import_preview", id=import_obj.id)

    return render(
        request, "mouse_import/import_form.html", {"form": form, "user": request.user}
    )


@login_required
def import_preview(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)

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
            return redirect("mouse_import:import_form")

    if df.empty:
        messages.error(
            request,
            "Selected range does not contain any data.",
            extra_tags="range_error",
        )
        return redirect("mouse_import:import_form")

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


@login_required
def import_commit(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)
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
