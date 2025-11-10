import pytest
from datetime import date
from pathlib import Path

from mouse_import.services.io_excel import read_range
from mouse_import.services.importer import Importer, ImportOptions
from mouseapp.models import Project, Mouse, Strain


def run_import(
    project_id: int, sheet: str, cell_range: str, mapping: dict[str, str]
) -> tuple[list[int], list[int], list[str]]:
    frame = read_range(Path(__file__).with_name("sheet.xlsx"), sheet, cell_range)
    return Importer(
        ImportOptions(
            project_id=project_id,
            sheet=sheet,
            range_expr=cell_range,
        )
    ).run(frame, mapping)


MAPPING: dict[str, str] = {
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
    project = Project(name="Test Project", start_date=date(2000, 1, 1))
    project.save()
    return project


def test_basic_import(project):
    created, updated, errors = run_import(project.id, "Sheet1", "A1:J3", MAPPING)
    assert not errors and not updated

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.father:
        m1, m2 = m2, m1

    assert m1.project == project
    assert m1.tube_number == 1
    assert m1.date_of_birth.year == 1970
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == Strain.objects.get_or_create("Some-strain")[0]
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    assert m2.project == project
    assert m2.father == m1


def test_import_same_tube_different_strain(project):
    """Same tube number but different (strain, tube_number) are different unique mice."""
    created, updated, errors = run_import(project.id, "Sheet2", "A1:J3", MAPPING)
    assert not errors and not updated
    assert len(created) == 2

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    # normalise order
    if m1.strain != "Some-strain":
        m1, m2 = m2, m1

    # row 1 mice
    assert m1.project == project
    assert m1.tube_number == 1
    assert m1.date_of_birth.isoformat() == "1970-01-01"
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == "Some-strain"
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    # row 2 mice
    assert m2.project == project
    assert m2.tube_number == 1
    assert m2.date_of_birth.isoformat() == "1970-01-02"
    assert m2.earmark == "TR"
    assert m2.sex == "F"
    assert m2.strain == "Different-strain"
    assert m2.coat_colour == "green"
    assert m2.father is None
    assert m2.mother is None
    assert m2.notes == ""
