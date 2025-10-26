from __future__ import annotations

from os import PathLike
import logging
import re
from contextlib import closing
from typing import cast
import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

_RANGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", re.I)


def read_range(
    file_path: PathLike, sheet_name: str | None, range_expr: str
) -> pd.DataFrame:
    with closing(
        load_workbook(filename=file_path, data_only=True, read_only=True)
    ) as workbook:
        worksheet = workbook[sheet_name] if sheet_name else workbook.active
        worksheet = cast(Worksheet, worksheet)

        match = _RANGE_RE.match(range_expr.replace(" ", ""))
        if not match:
            raise ValueError(f"Invalid range format: {range_expr}")

        c1, r1, c2, r2 = match.groups()
        rows = worksheet[f"{c1}{r1}":f"{c2}{r2}"]
        data = [[cell.value for cell in row] for row in rows]
        if not data:
            raise ValueError("Selected range does not contain any cells.")

        header = [str(v or "").strip() for v in data[0]]
        cols = pd.Index(header)
        df = pd.DataFrame(data[1:], columns=cols)
        return _clean_dataframe(df)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.ffill()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
    return df
