from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd
from django.db import DatabaseError, IntegrityError, transaction

from mouseapp.models import Mouse, Project

from .mapping import apply_mapping, importable_fields
from .validators import missing_required
from .fks import link_self_foreign_keys

logger = logging.getLogger(__name__)


@dataclass
class ImportOptions:
    project_id: int
    sheet: str
    range_expr: str


class Importer:
    """Coordinate the end-to-end import of mouse rows from a DataFrame."""

    def __init__(self, options: ImportOptions):
        self.options = options
        self.project = Project.objects.get(pk=options.project_id)
        self.fields = list(importable_fields())
        self.field_by_name = {field.name: field for field in self.fields}
        self.has_tube = "tube_number" in self.field_by_name
        self.has_strain = "strain" in self.field_by_name

    def run(
        self, dataframe: pd.DataFrame, mapping: Dict[str, str]
    ) -> Tuple[List[int], List[int], List[str]]:
        """Persist DataFrame rows using the supplied mapping and project context."""

        created_ids: List[int] = []
        updated_ids: List[int] = []
        errors: List[str] = []
        pending_self_fk: List[Tuple[int, Dict[str, Any]]] = []

        for row_num, (_, row) in enumerate(dataframe.iterrows(), start=1):
            savepoint = transaction.savepoint()
            try:
                defaults, self_fk_raw = apply_mapping(
                    row, mapping, self.fields, self.project
                )
                missing = missing_required(self.fields, defaults)
                if missing:
                    errors.append(
                        f"Row {row_num}: missing/invalid required fields: {', '.join(missing)}"
                    )
                    transaction.savepoint_rollback(savepoint)
                    continue

                # if both strain and tube_number are present, update by that pair (ignore project in lookup)
                if (
                    self.has_tube
                    and self.has_strain
                    and defaults.get("tube_number") is not None
                    and defaults.get("strain") is not None
                ):
                    obj, was_created = Mouse.objects.update_or_create(
                        tube_number=defaults["tube_number"],
                        strain=defaults["strain"],
                        defaults=defaults,
                    )
                # else keep prior behavior
                elif self.has_tube and defaults.get("tube_number") is not None:
                    obj, was_created = Mouse.objects.update_or_create(
                        project=self.project,
                        tube_number=defaults["tube_number"],
                        defaults=defaults,
                    )
                else:
                    obj = Mouse.objects.create(**defaults)
                    was_created = True

                if was_created:
                    created_ids.append(obj.pk)
                else:
                    updated_ids.append(obj.pk)

                if self_fk_raw:
                    pending_self_fk.append((obj.pk, self_fk_raw))

                transaction.savepoint_commit(savepoint)
            except (IntegrityError, DatabaseError) as db_exc:
                transaction.savepoint_rollback(savepoint)
                errors.append(f"Row {row_num}: database error: {db_exc}")
                logger.warning(
                    "Row import failed due to database error", exc_info=db_exc
                )
            except Exception as exc:
                transaction.savepoint_rollback(savepoint)
                errors.append(f"Row {row_num}: error: {exc}")
                logger.warning("Row import failed", exc_info=exc)

        link_self_foreign_keys(
            pending_self_fk, self.field_by_name, self.project, errors
        )
        return created_ids, updated_ids, errors
