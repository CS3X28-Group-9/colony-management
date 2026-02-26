import pytest
from datetime import date
from pathlib import Path


from mouse_import.services.io import read_range
from mouse_import.services.importer import Importer, ImportOptions
from mouseapp.models import Project, Mouse, Strain


def run_import_xlsx(
    project_id: int,
    sheet: str,
    cell_range: str,
    fixed_fields: dict[str, str],
    mapping: dict[str, str],
) -> tuple[list[int], list[int], list[str]]:
    frame = read_range(
        Path(__file__).with_name("sheet.xlsx"),
        sheet,
        cell_range,
        original_filename="sheet.xlsx",
        mapping=mapping,
    )
    return Importer(
        ImportOptions(
            project_id=project_id,
            sheet=sheet,
            range_expr=cell_range,
        )
    ).run(frame, fixed_fields, mapping)


def run_import_csv(
    project_id: int,
    sheet: str,
    cell_range: str,
    fixed_fields: dict[str, str],
    mapping: dict[str, str],
) -> tuple[list[int], list[int], list[str]]:
    # Sheet is ignored for CSV, but we keep the same call shape.
    frame = read_range(
        Path(__file__).with_name("sheet.csv"),
        sheet,
        cell_range,
        original_filename="sheet.csv",
        mapping=mapping,
    )
    return Importer(
        ImportOptions(
            project_id=project_id,
            sheet=sheet,
            range_expr=cell_range,
        )
    ).run(frame, fixed_fields, mapping)


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
    "cull_date": "Cull Date",
    "cull_reason": "Cull Reason",
}


def strain(n):
    return Strain.objects.get_or_create(name=n)[0]


@pytest.fixture
def project(db):
    project = Project(name="Test Project", start_date=date(2000, 1, 1))
    project.save()
    return project


def test_basic_import(project):
    created, updated, errors = run_import_xlsx(
        project.id, "Sheet1", "A1:J3", {}, MAPPING
    )
    assert not errors and not updated

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.father:
        m1, m2 = m2, m1

    assert m1.project == project
    assert m1.tube_number == 1
    assert m1.date_of_birth.year == 1970
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == strain("Some-strain")
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    assert m2.project == project
    assert m2.father == m1


def test_fixed_strain(project):
    created, updated, errors = run_import_xlsx(
        project.id, "Sheet1", "A1:J2", {"strain": "some-fixed-strain"}, MAPPING
    )

    assert not errors and not updated
    (m_id,) = created
    mouse = Mouse.objects.get(pk=m_id)
    assert mouse.strain is not None
    assert mouse.strain.name == "some-fixed-strain"


def test_parent_strain_filtering(project):
    created, updated, errors = run_import_xlsx(
        project.id, "Sheet1", "A1:J2", {"strain": "some-fixed-strain"}, MAPPING
    )
    assert not errors and not updated

    created, updated, errors = run_import_xlsx(
        project.id, "Sheet1", "A1:J3", {}, MAPPING
    )

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.father:
        m1, m2 = m2, m1

    assert m2.father == m1


def test_import_same_tube_different_strain(project):
    """Same tube number but different (strain, tube_number) are different unique mice."""
    created, updated, errors = run_import_xlsx(
        project.id, "Sheet2", "A1:J3", {}, MAPPING
    )
    assert not errors and not updated
    assert len(created) == 2

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.strain != strain("Some-strain"):
        m1, m2 = m2, m1

    assert m1.project == project
    assert m1.tube_number == 1
    assert m1.date_of_birth.isoformat() == "1970-01-01"
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == strain("Some-strain")
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    assert m2.project == project
    assert m2.tube_number == 1
    assert m2.date_of_birth.isoformat() == "1970-01-02"
    assert m2.earmark == "TR"
    assert m2.sex == "F"
    assert m2.strain == strain("Different-strain")
    assert m2.coat_colour == "green"
    assert m2.father is None
    assert m2.mother is None
    assert m2.notes == ""


def test_read_range_csv_matches_excel_sheet2():
    """
    Your sheet.csv is the export of sheet.xlsx/Sheet2.
    This locks in 'same range semantics' between Excel and CSV.
    """
    xlsx = read_range(
        Path(__file__).with_name("sheet.xlsx"),
        "Sheet2",
        "A1:J3",
        original_filename="sheet.xlsx",
    )
    csv_df = read_range(
        Path(__file__).with_name("sheet.csv"),
        "Sheet2",  # ignored
        "A1:J3",
        original_filename="sheet.csv",
    )

    assert xlsx.to_dict(orient="records") == csv_df.to_dict(orient="records")
    assert list(xlsx.columns) == list(csv_df.columns)


def test_import_same_tube_different_strain_csv(project):
    """
    CSV version of Sheet2: same expected behaviour as the Excel test above.
    """
    created, updated, errors = run_import_csv(
        project.id, "Sheet2", "A1:J3", {}, MAPPING
    )
    assert not errors and not updated
    assert len(created) == 2

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.strain != strain("Some-strain"):
        m1, m2 = m2, m1

    assert m1.project == project
    assert m1.tube_number == 1
    assert m1.date_of_birth.isoformat() == "1970-01-01"
    assert m1.earmark == "TL"
    assert m1.sex == "M"
    assert m1.strain == strain("Some-strain")
    assert m1.coat_colour == "black"
    assert m1.father is None
    assert m1.mother is None
    assert m1.notes == ""

    assert m2.project == project
    assert m2.tube_number == 1
    assert m2.date_of_birth.isoformat() == "1970-01-02"
    assert m2.earmark == "TR"
    assert m2.sex == "F"
    assert m2.strain == strain("Different-strain")
    assert m2.coat_colour == "green"
    assert m2.father is None
    assert m2.mother is None
    assert m2.notes == ""


def test_import_cull_forwardfill(project):
    created, updated, errors = run_import_csv(
        project.id, "Sheet1", "A1:L3", {}, MAPPING
    )

    assert not errors and not updated
    assert len(created) == 2

    m1, m2 = [Mouse.objects.get(pk=pk) for pk in created]
    if m1.strain != strain("Some-strain"):
        m1, m2 = m2, m1

    assert m1.cull_date and m1.cull_date.isoformat() == "2024-01-01"
    assert m1.cull_reason == "Age"
    assert m2.cull_date is None
    assert m2.cull_reason is None
