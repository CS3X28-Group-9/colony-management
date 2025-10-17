from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
from django.utils.dateparse import parse_date

logger = logging.getLogger(__name__)


def to_int(value: Any) -> Optional[int]:
    """Cast values coming from Excel into integers when possible."""

    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        logger.debug("Failed to coerce value to int", extra={"value": value})
        return None


def to_date(value: Any):
    """Normalise Excel values into :class:`datetime.date` objects."""

    if value in (None, ""):
        return None
    try:
        as_datetime = pd.to_datetime(value, errors="coerce")
        if pd.isna(as_datetime):
            return parse_date(str(value))
        return as_datetime.date()
    except Exception:
        return parse_date(str(value))


def to_bool(value: Any) -> Optional[bool]:
    """Interpret checkboxes and textual booleans consistently."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "y", "yes", "✓", "x"}:
        return True
    if text in {"0", "false", "f", "n", "no"}:
        return False
    return None


def to_text(value: Any) -> str:
    """Ensure textual fields are persisted without surrounding whitespace."""

    return "" if value is None else str(value).strip()


def normalize_for_field(field, raw_value: Any):
    """Match Django model field expectations without altering semantics."""

    internal_type = field.get_internal_type()

    if internal_type in {
        "IntegerField",
        "PositiveIntegerField",
        "BigIntegerField",
        "AutoField",
    }:
        return to_int(raw_value)

    if internal_type == "DateField":
        return to_date(raw_value)

    if internal_type == "BooleanField":
        coerced = to_bool(raw_value)
        return bool(coerced) if coerced is not None else False

    choices = getattr(field, "choices", None)
    if choices:
        if raw_value is None:
            return None
        text = str(raw_value).strip()
        for key, _ in choices:
            if str(key).lower() == text.lower():
                return key
        for key, label in choices:
            if str(label).lower() == text.lower():
                return key
        if len(text) == 1:
            for key, _ in choices:
                if str(key).lower().startswith(text.lower()):
                    return key
        return None

    return to_text(raw_value)
