import pytest
from django.urls import reverse

from mouse_import.models import MouseImport


pytestmark = pytest.mark.django_db


@pytest.fixture
def import_obj(project, user, media_root, uploaded_xlsx):
    return MouseImport.objects.create(
        uploaded_by=user,
        project=project,
        file=uploaded_xlsx,
        original_filename="sheet.xlsx",
        sheet_name="",
        cell_range="",
    )


def test_import_form_upload_redirects_to_range_step(
    authed_client, project, uploaded_xlsx, media_root
):
    resp = authed_client.post(
        reverse("mouse_import:import_form"),
        {"project": project.id, "file": uploaded_xlsx},
    )

    assert resp.status_code == 302

    import_obj = MouseImport.objects.get()
    assert resp.url == reverse(
        "mouse_import:import_select_range", kwargs={"id": import_obj.id}
    )

    assert import_obj.project == project
    assert import_obj.original_filename == "sheet.xlsx"
    assert import_obj.sheet_name == ""
    assert import_obj.cell_range == ""
    assert import_obj.uploaded_by is not None


def test_import_select_range_get_renders_second_step(authed_client, import_obj):
    resp = authed_client.get(
        reverse("mouse_import:import_select_range", kwargs={"id": import_obj.id})
    )

    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Step 2" in content
    assert "Select sheet and cell range" in content
    assert 'name="sheet_name"' in content
    assert 'name="cell_range"' in content


def test_import_select_range_post_saves_range_and_clears_session(
    authed_client, import_obj
):
    session = authed_client.session
    session[f"import_df_{import_obj.id}"] = "stale-df"
    session[f"import_map_{import_obj.id}"] = {"stale": True}
    session.save()

    resp = authed_client.post(
        reverse("mouse_import:import_select_range", kwargs={"id": import_obj.id}),
        {"sheet_name": "Sheet1", "cell_range": " a1 : j3 "},
    )

    assert resp.status_code == 302
    assert resp.url == reverse(
        "mouse_import:import_preview", kwargs={"id": import_obj.id}
    )

    import_obj.refresh_from_db()
    assert import_obj.sheet_name == "Sheet1"
    assert import_obj.cell_range == "A1:J3"

    session = authed_client.session
    assert f"import_df_{import_obj.id}" not in session
    assert f"import_map_{import_obj.id}" not in session


def test_import_preview_redirects_back_to_range_step_if_range_missing(
    authed_client, import_obj
):
    resp = authed_client.get(
        reverse("mouse_import:import_preview", kwargs={"id": import_obj.id})
    )

    assert resp.status_code == 302
    assert resp.url == reverse(
        "mouse_import:import_select_range", kwargs={"id": import_obj.id}
    )


def test_import_commit_redirects_back_to_range_step_if_range_missing(
    authed_client, import_obj
):
    resp = authed_client.post(
        reverse("mouse_import:import_commit", kwargs={"id": import_obj.id})
    )

    assert resp.status_code == 302
    assert resp.url == reverse(
        "mouse_import:import_select_range", kwargs={"id": import_obj.id}
    )


def test_import_range_preview_returns_boundaries_and_truncated_preview(
    authed_client, import_obj
):
    resp = authed_client.get(
        reverse("mouse_import:import_range_preview", kwargs={"id": import_obj.id}),
        {"sheet": "Sheet1", "cell_range": "A1:O20"},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["boundaries"] == {
        "first_row": 1,
        "last_row": 20,
        "first_column": "A",
        "last_column": "O",
    }

    assert len(payload["columns"]) == 12
    assert len(payload["rows"]) == 10
    assert payload["truncated"]["columns"] is True
    assert payload["truncated"]["rows"] is True
    assert payload["rows"][0][0].endswith("…")


def test_import_range_preview_rejects_invalid_range(authed_client, import_obj):
    resp = authed_client.get(
        reverse("mouse_import:import_range_preview", kwargs={"id": import_obj.id}),
        {"sheet": "Sheet1", "cell_range": "nope"},
    )

    assert resp.status_code == 400
    assert resp.json() == {"error": 'Enter a range like "A1:M40"'}


def test_import_range_preview_rejects_invalid_sheet(authed_client, import_obj):
    resp = authed_client.get(
        reverse("mouse_import:import_range_preview", kwargs={"id": import_obj.id}),
        {"sheet": "Nope", "cell_range": "A1:B2"},
    )

    assert resp.status_code == 400
    assert resp.json() == {"error": "Select a valid sheet."}
