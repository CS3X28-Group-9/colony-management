from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from django.db.models import Field, NOT_PROVIDED

__all__ = [
    "field_required",
    "missing_required",
    "parse_cell_range",
    "normalise_cell_range",
    "cell_range_boundaries",
    "excel_col_to_index",
]


_CELL_RANGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", re.I)


def field_required(field: Field) -> bool:
    """Mirror Django's required semantics for model fields."""

    has_default = getattr(field, "default", NOT_PROVIDED) is not NOT_PROVIDED
    return (
        not getattr(field, "null", False)
        and not getattr(field, "blank", False)
        and not has_default
    )


def missing_required(fields: Iterable[Field], values: Dict[str, Any]) -> List[str]:
    """Return model field names that are still missing after mapping."""

    missing: List[str] = []
    for field in fields:
        if not field_required(field):
            continue
        value = values.get(field.name)
        internal_type = field.get_internal_type()
        if internal_type in {"CharField", "TextField"}:
            if value in (None, ""):
                missing.append(field.name)
        else:
            if value is None:
                missing.append(field.name)
    return missing


def excel_col_to_index(col: str) -> int:
    """Convert Excel-style column (A, B, ..., Z, AA, AB, ...) to a 0-based index."""

    col = (col or "").strip().upper()
    if not col:
        raise ValueError("Invalid range format: missing column")

    n = 0
    for ch in col:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Invalid range format: {col}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def parse_cell_range(range_expr: str) -> tuple[str, int, str, int]:
    """
    Parse an Excel range like "A1:M40".

    Returns: (first_col, first_row, last_col, last_row) with columns uppercased.
    Raises ValueError with slightly detailed messages.
    """

    expr = (range_expr or "").replace(" ", "").strip()
    match = _CELL_RANGE_RE.match(expr)
    if not match:
        raise ValueError('Enter a range like "A1:M40"')

    c1, r1_s, c2, r2_s = match.groups()
    c1 = c1.upper()
    c2 = c2.upper()

    try:
        r1 = int(r1_s)
        r2 = int(r2_s)
    except ValueError:
        raise ValueError('Enter a range like "A1:M40"')

    if r1 < 1 or r2 < 1:
        raise ValueError("Row numbers must be 1 or greater")
    if r2 < r1:
        raise ValueError("Range rows must be top-to-bottom (e.g. A1:M40)")

    if excel_col_to_index(c2) < excel_col_to_index(c1):
        raise ValueError("Range columns must be left-to-right (e.g. A1:M40)")

    return c1, r1, c2, r2


def normalise_cell_range(range_expr: str) -> str:
    """Normalise user input to a canonical "A1:M40" format."""

    c1, r1, c2, r2 = parse_cell_range(range_expr)
    return f"{c1}{r1}:{c2}{r2}"


def cell_range_boundaries(range_expr: str) -> Dict[str, Any]:
    c1, r1, c2, r2 = parse_cell_range(range_expr)
    return {
        "first_row": r1,
        "last_row": r2,
        "first_column": c1,
        "last_column": c2,
    }
