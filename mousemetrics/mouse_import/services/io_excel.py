from __future__ import annotations

import logging
import re
from typing import Optional

import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

_RANGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", re.I)


def read_range(
    file_path: str, sheet_name: Optional[str], range_expr: str
) -> pd.DataFrame:
    """Read and normalise a rectangular Excel range into a DataFrame."""

    logger.debug(
        "Reading Excel range",
        extra={"path": file_path, "sheet": sheet_name, "range": range_expr},
    )
    workbook = load_workbook(filename=file_path, data_only=True, read_only=True)
    try:
        worksheet = workbook[sheet_name] if sheet_name else workbook.active

        match = _RANGE_RE.match(range_expr.replace(" ", ""))
        if not match:
            logger.error("Invalid Excel range expression", extra={"range": range_expr})
            raise ValueError(f"Invalid range format: {range_expr}")

        col_start, row_start, col_end, row_end = match.groups()
        rows = worksheet[f"{col_start}{row_start}":f"{col_end}{row_end}"]
        data = [[cell.value for cell in row] for row in rows]

        if not data:
            raise ValueError("Selected range does not contain any cells.")

        header = [str(value or "").strip() for value in data[0]]
        df = pd.DataFrame(data[1:], columns=header)
        return _clean_dataframe(df)
    finally:
        workbook.close()


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same cleaning pipeline used prior to committing data."""

    if df.empty:
        return df

    df = df.ffill()
    for column in df.select_dtypes(include=["object"]):
        df[column] = df[column].apply(
            lambda value: value.strip() if isinstance(value, str) else value
        )
    return df
