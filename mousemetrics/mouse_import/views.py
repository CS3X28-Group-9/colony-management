from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render


from .forms import ColumnMappingForm, MouseImportForm
from .models import MouseImport
from .services.importer import ImportOptions, Importer
from .services.io_excel import read_range

MICE_PAGE_SIZE = 50
PREVIEW_ROW_LIMIT = 50


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

    return render(request, "mouse_import/import_form.html", {"form": form})


@login_required
def import_preview(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)
    print("PREVIEW → id:", import_obj.id, "cell_range:", repr(import_obj.cell_range))

    try:
        df = read_range(
            import_obj.file.path,
            import_obj.sheet_name,
            import_obj.cell_range,
        )
    except Exception as exc:  # pragma: no cover - reported to the user
        messages.error(
            request, f"Error reading Excel range: {exc}", extra_tags="range_error"
        )
        return redirect("mouse_import:import_form")

    if df.empty:
        messages.error(
            request,
            "Selected range does not contain any data.",
            extra_tags="range_error",
        )
        return redirect("mouse_import:import_form")

    df_key = _df_session_key(import_obj.id)
    map_key = _map_session_key(import_obj.id)

    request.session[df_key] = df.to_json(orient="records")
    columns = list(df.columns)
    import_obj.row_count = len(df)
    import_obj.save(update_fields=["row_count"])

    saved_initial, saved_fixed, saved_mapping = request.session.get(map_key) or (
        None,
        None,
        None,
    )

    if request.method == "POST":
        form = ColumnMappingForm(
            request.POST, columns=columns, project=import_obj.project
        )
        if form.is_valid():
            request.session[map_key] = form.selected_mapping()
            messages.success(request, "Column mapping saved.")
            return redirect("mouse_import:import_preview", id=import_obj.id)
    else:
        form = ColumnMappingForm(
            columns=columns, initial=saved_initial, project=import_obj.project
        )

    preview_rows = df.head(PREVIEW_ROW_LIMIT).to_dict(orient="records")

    context: Dict[str, Any] = {
        "import_obj": import_obj,
        "columns": columns,
        "rows": preview_rows,
        "form": form,
        "saved_mapping": saved_mapping,
        "saved_fixed": saved_fixed,
    }
    return render(request, "mouse_import/import_preview.html", context)


@login_required
def import_commit(request: HttpRequest, id: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, id=id)
    df_key = _df_session_key(import_obj.id)
    map_key = _map_session_key(import_obj.id)

    raw_df = request.session.get(df_key)
    _, fixed, mapping = request.session.get(map_key) or (None, None, None)

    if raw_df is None or mapping is None or fixed is None:
        messages.error(
            request,
            "Missing preview data or column mapping. Please re-upload and save the mapping.",
        )
        return redirect("mouse_import:import_preview", id=import_obj.id)

    df = pd.read_json(raw_df, orient="records")
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
