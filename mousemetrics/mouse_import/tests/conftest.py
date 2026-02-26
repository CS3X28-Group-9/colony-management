import pytest
from mouseapp.models import Project


@pytest.fixture
def project(db):
    return Project.objects.create(
        name="P",
        start_date="2000-01-01",
        license_constraints="",
    )
