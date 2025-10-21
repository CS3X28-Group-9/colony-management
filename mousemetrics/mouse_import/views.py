from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from mouseapp.models import Mouse, Project

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
        return redirect("mouse_import:import_preview", pk=import_obj.pk)

    return render(request, "mouse_import/import_form.html", {"form": form})


@login_required
def import_preview(request: HttpRequest, pk: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, pk=pk)

    try:
        df = read_range(
            import_obj.file.path,
            import_obj.sheet_name,
            import_obj.cell_range,
        )
    except Exception as exc:  # pragma: no cover - reported to the user
        messages.error(request, f"Error reading Excel range: {exc}")
        return redirect("mouse_import:import_form")

    if df.empty:
        messages.error(request, "Selected range does not contain any data.")
        return redirect("mouse_import:import_form")

    df_key = _df_session_key(import_obj.pk)
    map_key = _map_session_key(import_obj.pk)

    request.session[df_key] = df.to_json(orient="records")
    columns = list(df.columns)
    import_obj.row_count = len(df)
    import_obj.save(update_fields=["row_count"])

    saved_mapping = request.session.get(map_key)

    if request.method == "POST":
        form = ColumnMappingForm(request.POST, columns=columns)
        if form.is_valid():
            request.session[map_key] = form.selected_mapping()
            messages.success(request, "Column mapping saved.")
            return redirect("mouse_import:import_preview", pk=import_obj.pk)
    else:
        initial = {
            f"map_{field}": column
            for field, column in (saved_mapping or {}).items()
            if column
        }
        form = ColumnMappingForm(columns=columns, initial=initial)

    preview_rows = df.head(PREVIEW_ROW_LIMIT).to_dict(orient="records")

    context: Dict[str, Any] = {
        "import_obj": import_obj,
        "columns": columns,
        "rows": preview_rows,
        "form": form,
        "saved_mapping": saved_mapping,
    }
    return render(request, "mouse_import/import_preview.html", context)


@login_required
def import_commit(request: HttpRequest, pk: int) -> HttpResponse:
    import_obj = get_object_or_404(MouseImport, pk=pk)
    df_key = _df_session_key(import_obj.pk)
    map_key = _map_session_key(import_obj.pk)

    raw_df = request.session.get(df_key)
    mapping = request.session.get(map_key)

    if raw_df is None or mapping is None:
        messages.error(
            request,
            "Missing preview data or column mapping. Please re-upload and save the mapping.",
        )
        return redirect("mouse_import:import_preview", pk=import_obj.pk)

    df = pd.read_json(raw_df, orient="records")
    importer = Importer(
        ImportOptions(
            project_id=import_obj.project_id,
            sheet=import_obj.sheet_name or "",
            range_expr=import_obj.cell_range,
        )
    )
    created_ids, updated_ids, errors = importer.run(df, mapping)

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


def mice_list(request: HttpRequest) -> HttpResponse:
    project_id = request.GET.get("project")

    queryset = Mouse.objects.select_related("project", "box").order_by(
        "project_id",
        "tube_number",
    )
    if project_id:
        queryset = queryset.filter(project_id=project_id)

    paginator = Paginator(queryset, MICE_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page": page_obj,
        "projects": Project.objects.all().order_by("id"),
        "selected_project": project_id or "",
    }
    return render(request, "mouse_import/mice_list.html", context)
