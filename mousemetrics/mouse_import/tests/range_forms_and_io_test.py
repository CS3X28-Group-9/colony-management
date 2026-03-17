import re
import pytest

from mouse_import.forms import MouseImportForm, MouseImportSheetRangeForm
from mouse_import.models import MouseImport
from mouse_import.services.io import list_sheet_names, read_range
from mouse_import.services.validators import (
    cell_range_boundaries,
    excel_col_to_index,
    normalise_cell_range,
    parse_cell_range,
)


pytestmark = pytest.mark.django_db


def test_mouse_import_form_is_upload_only():
    form = MouseImportForm()
    assert list(form.fields) == ["project", "file"]


def test_sheet_range_form_populates_choices_and_normalises_range():
    import_obj = MouseImport(sheet_name="Legacy Sheet", cell_range="A1:B2")

    form = MouseImportSheetRangeForm(
        data={"sheet_name": "Sheet1", "cell_range": " a1 : b2 "},
        instance=import_obj,
        sheet_choices=["Sheet1", "Sheet2"],
    )
    choices = list(form.fields["sheet_name"].widget.choices)

    assert ("", "(active)") in choices
    assert ("Sheet1", "Sheet1") in choices
    assert ("Sheet2", "Sheet2") in choices
    assert ("Legacy Sheet", "Legacy Sheet") in choices

    assert form.is_valid()
    assert form.cleaned_data["sheet_name"] == "Sheet1"
    assert form.cleaned_data["cell_range"] == "A1:B2"


def test_sheet_range_form_rejects_unknown_sheet():
    form = MouseImportSheetRangeForm(
        data={"sheet_name": "Nope", "cell_range": "A1:B2"},
        sheet_choices=["Sheet1", "Sheet2"],
    )

    assert not form.is_valid()
    assert form.errors["sheet_name"] == ["Select a valid sheet."]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A1:M40", ("A", 1, "M", 40)),
        (" a1 : m40 ", ("A", 1, "M", 40)),
        ("AA10:AB12", ("AA", 10, "AB", 12)),
    ],
)
def test_parse_cell_range(raw, expected):
    assert parse_cell_range(raw) == expected


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", 'Enter a range like "A1:M40"'),
        ("A1", 'Enter a range like "A1:M40"'),
        ("A0:B2", "Row numbers must be 1 or greater"),
        ("A2:B1", "Range rows must be top-to-bottom (e.g. A1:M40)"),
        ("C1:A2", "Range columns must be left-to-right (e.g. A1:M40)"),
    ],
)
def test_parse_cell_range_rejects_invalid_ranges(raw, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        parse_cell_range(raw)


def test_normalise_cell_range():
    assert normalise_cell_range(" a1 : m40 ") == "A1:M40"


def test_cell_range_boundaries():
    assert cell_range_boundaries("b2:d10") == {
        "first_row": 2,
        "last_row": 10,
        "first_column": "B",
        "last_column": "D",
    }


def test_excel_col_to_index():
    assert excel_col_to_index("A") == 0
    assert excel_col_to_index("Z") == 25
    assert excel_col_to_index("AA") == 26
    assert excel_col_to_index("AB") == 27


def test_list_sheet_names_for_excel_and_csv(sheet_xlsx_path, sheet_csv_path):
    assert list_sheet_names(sheet_xlsx_path, original_filename="sheet.xlsx") == [
        "Sheet1",
        "Sheet2",
    ]
    assert list_sheet_names(sheet_csv_path, original_filename="sheet.csv") == []


def test_read_range_limit_applies_to_excel_and_csv(sheet_xlsx_path, sheet_csv_path):
    xlsx = read_range(
        sheet_xlsx_path,
        "Sheet2",
        "A1:J3",
        original_filename="sheet.xlsx",
        limit=1,
    )
    csv_df = read_range(
        sheet_csv_path,
        "Sheet2",
        "A1:J3",
        original_filename="sheet.csv",
        limit=1,
    )

    assert len(xlsx) == 1
    assert len(csv_df) == 1
    assert list(xlsx.columns) == list(csv_df.columns)
    assert xlsx.to_dict(orient="records") == csv_df.to_dict(orient="records")
