from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from mouseapp.models import Project


@pytest.fixture
def project(db):
    return Project.objects.create(
        name="P",
        start_date="2000-01-01",
        license_constraints="",
    )


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="importer", password="x")


@pytest.fixture
def authed_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def sheet_xlsx_path():
    return Path(__file__).with_name("sheet.xlsx")


@pytest.fixture
def sheet_csv_path():
    return Path(__file__).with_name("sheet.csv")


@pytest.fixture
def view_xlsx_path():
    return Path(__file__).with_name("view_sheet.xlsx")


@pytest.fixture
def uploaded_xlsx(view_xlsx_path):
    return SimpleUploadedFile(
        "sheet.xlsx",
        view_xlsx_path.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
