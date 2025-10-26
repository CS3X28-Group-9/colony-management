from __future__ import annotations

import logging
from typing import Any, Iterable, Iterator

from django.db.models import Field, ForeignKey

from mouseapp.models import Mouse

from .coercion import normalize_for_field
from .fks import resolve_fk_instance

logger = logging.getLogger(__name__)

__all__ = ["importable_fields", "apply_mapping"]


def importable_fields() -> Iterator[Field[Any, Any]]:
    """Yield Mouse model fields that can be populated by imports."""

    excluded = {"id", "project"}
    for field in Mouse._meta.get_fields():
        if getattr(field, "many_to_many", False) or getattr(
            field, "one_to_many", False
        ):
            continue
        if getattr(field, "auto_created", False):
            continue
        if not getattr(field, "editable", True):
            continue
        if field.name in excluded:
            continue
        if not isinstance(field, Field):
            continue
        yield field


def apply_mapping(
    row,
    mapping: dict[str, str],
    fields: Iterable[Field],
    project,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate a pandas row into model-ready defaults and deferred relations."""

    defaults: dict[str, Any] = {"project": project}
    self_fk_raw: dict[str, Any] = {}

    for field in fields:
        column_name = mapping.get(field.name)
        if not column_name:
            continue

        raw_value = row.get(column_name)
        if isinstance(field, ForeignKey):
            if field.remote_field.model is Mouse:
                self_fk_raw[field.name] = raw_value
            else:
                defaults[field.name] = resolve_fk_instance(field, raw_value, project)
        else:
            defaults[field.name] = normalize_for_field(field, raw_value)

    logger.debug(
        "Applied column mapping",
        extra={
            "mapped_fields": [field for field in defaults.keys() if field != "project"],
            "deferred_fields": list(self_fk_raw.keys()),
        },
    )
    return defaults, self_fk_raw
