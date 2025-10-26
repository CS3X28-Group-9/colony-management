import pytest
from pathlib import Path

from mouse_import.services.io_excel import read_range
from mouse_import.services.importer import Importer, ImportOptions
from mouseapp.models import Project, Mouse


def run_import(
    project: int, sheet: str, range: str, mapping: dict[str, str]
) -> tuple[list[int], list[int], list[str]]:
    frame = read_range(Path(__file__).with_name("sheet.xlsx"), sheet, range)
    return Importer(
        ImportOptions(
            project_id=project,
            sheet=sheet,
            range_expr=range,
        )
    ).run(frame, mapping)


MAPPING = {
    "box": "Box",
    "tube_number": "Tube ID",
    "date_of_birth": "DOB",
    "earmark": "Earmark",
    "sex": "Sex",
    "strain": "Strain",
    "coat_colour": "Coat Colour",
    "father": "Father",
    "mother": "Mother",
    "notes": "Notes",
}


@pytest.fixture
def project(db):
    project = Project()
    project.save()
    return project


def test_basic_import(project):
    (created, updated, errors) = run_import(project.id, "Sheet1", "A1:J3", MAPPING)
    assert not errors and not updated
    (m1, m2) = [Mouse.objects.get(pk=id) for id in created]
    if m1.father:
        (m1, m2) = (m2, m1)

    assert m1.tube_number == 1
    assert m1.date_of_birth.year == 1970
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == "Some-strain"
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    assert m2.father.id == m1.id
