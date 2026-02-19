from __future__ import annotations

import csv
import logging
import re
from contextlib import closing
from os import PathLike
from pathlib import Path
from typing import cast

import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from datetime import date, datetime

logger = logging.getLogger(__name__)

_RANGE_RE = re.compile(r"^([A-Z]+)(\d+):([A-Z]+)(\d+)$", re.I)


def read_range(
    file_path: PathLike,
    sheet_name: str | None,
    range_expr: str,
    *,
    original_filename: str | None = None,
) -> pd.DataFrame:
    """
    Reads an Excel-like rectangular range (e.g. A1:M40) into a DataFrame.

    Behaviour mirrors the existing Excel importer:
      - first row is header (stringified + stripped)
      - blanks -> NA
      - forward-fill (ffill)
      - trim string cells

    Supports:
      - Excel workbooks via openpyxl
      - CSV files (delimiter auto-detected), with the SAME range semantics
    """
    match = _RANGE_RE.match(range_expr.replace(" ", ""))
    if not match:
        raise ValueError(f"Invalid range format: {range_expr}")

    c1, r1, c2, r2 = match.groups()

    ext = _infer_extension(file_path, original_filename)
    if ext == ".csv":
        return _read_csv_range(file_path, c1, r1, c2, r2)

    return _read_excel_range(file_path, sheet_name, c1, r1, c2, r2)


def _infer_extension(file_path: PathLike, original_filename: str | None) -> str:
    # Prefer original filename if available (storage paths can be weird).
    if original_filename:
        return Path(original_filename).suffix.lower()
    return Path(str(file_path)).suffix.lower()


def _read_excel_range(
    file_path: PathLike,
    sheet_name: str | None,
    c1: str,
    r1: str,
    c2: str,
    r2: str,
) -> pd.DataFrame:
    with closing(
        load_workbook(filename=file_path, data_only=True, read_only=True)
    ) as workbook:
        worksheet = workbook[sheet_name] if sheet_name else workbook.active
        worksheet = cast(Worksheet, worksheet)

        rows = worksheet[f"{c1}{r1}":f"{c2}{r2}"]
        data = [[cell.value for cell in row] for row in rows]
        if not data:
            raise ValueError("Selected range does not contain any cells.")

        header = [str(v or "").strip() for v in data[0]]
        cols = pd.Index(header)
        df = pd.DataFrame(data[1:], columns=cols)
        return _process_dataframe(df)


def _read_csv_range(
    file_path: PathLike,
    c1: str,
    r1: str,
    c2: str,
    r2: str,
) -> pd.DataFrame:
    c1i = _col_to_index(c1)
    c2i = _col_to_index(c2)

    # Rows are 1-indexed, inclusive.
    start_row = int(r1)
    end_row = int(r2)
    if end_row < start_row:
        raise ValueError("Selected range does not contain any cells.")

    skiprows = start_row - 1
    nrows = end_row - start_row + 1

    encoding = _detect_encoding(file_path)
    delimiter = _detect_delimiter(file_path, encoding)

    df_raw = pd.read_csv(
        file_path,
        encoding=encoding,
        sep=delimiter,
        header=None,
        dtype=object,
        skiprows=skiprows,
        nrows=nrows,
        engine="python",
        keep_default_na=False,
    )

    if df_raw.empty:
        raise ValueError("Selected range does not contain any cells.")

    # Pad out missing columns so selecting a "wider" range behaves like Excel (empties become NA).
    needed_cols = c2i + 1
    current_cols = df_raw.shape[1]
    if current_cols < needed_cols:
        for j in range(current_cols, needed_cols):
            df_raw[j] = pd.NA

    # Slice selected columns
    df_raw = df_raw.iloc[:, c1i : c2i + 1]

    if df_raw.empty:
        raise ValueError("Selected range does not contain any cells.")

    header = [str(v or "").strip() for v in df_raw.iloc[0].tolist()]
    df = df_raw.iloc[1:].copy()
    df.columns = pd.Index(header)
    return _process_dataframe(df)


def _col_to_index(col: str) -> int:
    # Convert Excel-style column (A, B, ..., Z, AA, AB, ...) to 0-based index.
    col = col.upper()
    n = 0
    for ch in col:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Invalid range format: {col}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _detect_encoding(file_path: PathLike) -> str:
    # try utf-8-sig and utf-16, then fall back to latin-1
    for enc in ("utf-8-sig", "utf-16"):
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                f.read(2048)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _detect_delimiter(file_path: PathLike, encoding: str) -> str:
    try:
        with open(file_path, "r", encoding=encoding, newline="") as f:
            sample = f.read(4096)

        # should work for most common delimiters
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","


def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    idxs = iter(range(len(df.columns)))
    df.columns = [col or f"unnamed-{next(idxs) + 1}" for col in df.columns]

    if df.empty:
        return df

    # blanks / whitespace -> NA
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # forward-fill
    df = df.ffill()

    # trim existing strings
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # pandas NA -> None
    df = df.astype("object").mask(pd.isna(df), None)

    # stable string output
    def _to_string(v):
        if v is None:
            return None
        if isinstance(v, pd.Timestamp):
            return v.date().isoformat()
        if isinstance(v, datetime):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return str(v).strip()

    for col in df.columns:
        df[col] = df[col].apply(_to_string)

    return df
