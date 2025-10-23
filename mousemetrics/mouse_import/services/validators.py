from __future__ import annotations

from typing import Any, Dict, Iterable, List

from django.db.models import Field, NOT_PROVIDED

__all__ = ["field_required", "missing_required"]


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
