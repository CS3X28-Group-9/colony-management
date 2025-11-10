from __future__ import annotations

import logging
from typing import Any, Dict

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ForeignKey, Model, Field

from mouseapp.models import Mouse, Box, Strain

from .coercion import normalize_for_field

logger = logging.getLogger(__name__)


def resolve_fk_instance(fk_field: ForeignKey, raw_value: Any, project=None):
    """Resolve foreign keys without surfacing DB errors to callers."""

    target_model = fk_field.remote_field.model

    if target_model is Mouse:
        tube_field = Mouse._meta.get_field("tube_number")
        tube_value = _coerce_for_field(tube_field, raw_value)
        if tube_value is None:
            return None

        qs = Mouse.objects.all()
        if project is not None:
            qs = qs.filter(project=project)
        return qs.filter(tube_number=tube_value).first()

    if target_model is Box:
        number_field = Box._meta.get_field("number")
        number_value = _coerce_for_field(number_field, raw_value)
        if number_value is None:
            return None

        qs = Box.objects.all()
        if project is not None:
            qs = qs.filter(project=project)
        box = qs.filter(number=number_value).first()
        if box:
            return box

        # Create box if it doesn't exist
        if project is not None:
            try:
                return Box.objects.create(project=project, number=number_value)
            except Exception:
                return None
        return None

    if target_model is Strain:
        return Strain.objects.get_or_create(name=str(raw_value))[0]

    pk_name = _target_pk_name(target_model)
    pk_field = _get_model_field(target_model, pk_name)
    pk_value = _coerce_for_field(pk_field, raw_value)

    if pk_value is None:
        return None

    existing = target_model.objects.filter(**{pk_name: pk_value}).first()
    if existing:
        return existing

    if not _pk_value_has_valid_type(pk_field, pk_value):
        return None

    try:
        return target_model.objects.create(**{pk_name: pk_value})
    except Exception:
        return None


def link_self_foreign_keys(
    pending: list[tuple[int, dict[str, Any]]],
    field_by_name: dict[str, Field],
    project,
    errors: list[str],
) -> None:
    """Resolve deferred parent links after initial row creation."""

    for pk, raw_map in pending:
        if not raw_map:
            continue

        sp = transaction.savepoint()
        try:
            updates: Dict[str, Any] = {}
            for field_name, raw_value in raw_map.items():
                field = field_by_name.get(field_name)
                if not field or not isinstance(field, ForeignKey):
                    continue
                if field.remote_field.model is not Mouse:
                    continue
                target = resolve_fk_instance(field, raw_value, project=project)
                if target:
                    updates[f"{field_name}_id"] = target.pk
            if updates:
                Mouse.objects.filter(pk=pk).update(**updates)
            transaction.savepoint_commit(sp)
        except (IntegrityError, DatabaseError) as db_exc:
            transaction.savepoint_rollback(sp)
            errors.append(
                f"Linking parents for mouse pk={pk}: database error: {db_exc}"
            )
            logger.warning("Failed to resolve self FK", exc_info=db_exc)
        except Exception as exc:
            transaction.savepoint_rollback(sp)
            errors.append(f"Linking parents for mouse pk={pk}: error: {exc}")
            logger.warning("Failed to resolve self FK", exc_info=exc)


def _target_pk_name(model_class: type[Model]) -> str:
    return model_class._meta.pk.name


def _get_model_field(model_class: type[Model], name: str):
    try:
        return model_class._meta.get_field(name)
    except Exception:
        return None


def _coerce_for_field(model_field, raw_value: Any):
    if model_field is None:
        return raw_value
    return normalize_for_field(model_field, raw_value)


def _pk_value_has_valid_type(field, value: Any) -> bool:
    if field is None:
        return True
    internal_type = field.get_internal_type()
    if internal_type in {
        "IntegerField",
        "PositiveIntegerField",
        "BigIntegerField",
        "AutoField",
    }:
        return isinstance(value, int)
    if internal_type in {"CharField", "TextField"}:
        return isinstance(value, str)
    return True
