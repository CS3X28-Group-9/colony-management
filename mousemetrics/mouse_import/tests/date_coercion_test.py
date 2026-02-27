import datetime as dt

import pandas as pd
import pytest

from mouse_import.services.coercion import to_date

from mouse_import.services.importer import Importer, ImportOptions


@pytest.mark.django_db
def test_import_accepts_common_date_formats(project):
    importer = Importer(
        ImportOptions(project_id=project.id, sheet="", range_expr="A1:C3")
    )

    df = pd.DataFrame(
        [
            {"Tube ID": "1", "Strain": "S1", "DOB": "1970-01-01"},
            {"Tube ID": "2", "Strain": "S1", "DOB": "1970-01-02 00:00:00"},
        ]
    )

    fixed = {"sex": "M", "box": "A1"}
    mapping = {"tube_number": "Tube ID", "strain": "Strain", "date_of_birth": "DOB"}

    created_ids, updated_ids, errors = importer.run(df, fixed, mapping)

    assert errors == [], f"Unexpected import errors: {errors}"
    assert len(created_ids) + len(updated_ids) == 2


@pytest.mark.parametrize(
    "raw, expected",
    [
        # common ISO-ish formats
        ("1970-01-01", dt.date(1970, 1, 1)),
        ("1970/01/01", dt.date(1970, 1, 1)),
        ("1970-01-01 13:45:00", dt.date(1970, 1, 1)),
        ("1970-01-01T13:45:00", dt.date(1970, 1, 1)),
        (" 1970-01-01 ", dt.date(1970, 1, 1)),  # whitespace
        # common UK-ish sheet exports
        (
            "01/02/2024",
            dt.date(2024, 2, 1),
        ),  # dd/mm/yyyy (note: relies on pandas inference)
        ("1/2/2024", dt.date(2024, 2, 1)),
        # actual Excel/Pandas date types
        (dt.date(2020, 2, 3), dt.date(2020, 2, 3)),
        (dt.datetime(2020, 2, 3, 10, 11, 12), dt.date(2020, 2, 3)),
        (pd.Timestamp("2020-02-03 10:11:12"), dt.date(2020, 2, 3)),
    ],
)
def test_to_date_parses_realistic_inputs(raw, expected):
    assert to_date(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
    ],
)
def test_to_date_handles_empty_inputs(raw):
    assert to_date(raw) is None
