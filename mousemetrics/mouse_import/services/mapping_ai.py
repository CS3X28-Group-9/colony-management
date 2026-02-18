from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import pandas as pd
from django.db.utils import OperationalError, ProgrammingError

from mouseapp.models import Mouse
from mouse_import.models import (
    MouseImport,
    MouseImportMappingExample,
    MouseImportMappingModelState,
)
from mouse_import.targets import get_mouse_import_targets


_NON_ALNUM = re.compile(r"[^a-z0-9]+", re.I)
_WS = re.compile(r"\s+")

SAMPLE_VALUES_N = 12
TOP_VALUES_N = 6

DEFAULT_OPTIONAL_THRESHOLD = 0.45  # slightly conservative

FIELD_SYNONYMS: dict[str, list[str]] = {
    "date_of_birth": ["dob", "date of birth", "birth date", "birthday"],
    "tube_number": [
        "tube id",
        "tube #",
        "tube no",
        "tag",
        "tag id",
        "identifier",
        "id",
    ],
    "earmark": ["ear mark", "ear tag", "earmark"],
    "coat_colour": ["coat colour", "coat color", "colour", "color"],
    "sex": ["sex", "gender"],
    "father": ["father", "sire", "dad"],
    "mother": ["mother", "dam", "mum", "mom"],
    "notes": ["notes", "comment", "comments", "remarks", "remark"],
    "box": ["box", "cage", "location"],
    "strain": ["strain", "line"],
}


def _normalise_text(s: str) -> str:
    s = (s or "").strip().lower().replace("_", " ")
    s = _NON_ALNUM.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _header_similarity(header: str, field_name: str, verbose: str) -> float:
    h = _normalise_text(header)
    if not h:
        return 0.0
    candidates = [field_name, field_name.replace("_", " "), verbose]
    candidates.extend(FIELD_SYNONYMS.get(field_name, []))
    best = 0.0
    for c in candidates:
        c2 = _normalise_text(c)
        if not c2:
            continue
        if h == c2:
            return 1.0
        best = max(best, _seq_ratio(h, c2))
    return float(best)


def _build_column_text(header: str, series: pd.Series) -> str:
    vals: list[str] = []
    for v in series.tolist():
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        vals.append(s)
        if len(vals) >= 250:
            break

    sample_vals = vals[:SAMPLE_VALUES_N]
    top = Counter(vals).most_common(TOP_VALUES_N)

    parts = [f"Header: {header}"]
    if sample_vals:
        parts.append("Examples: " + " | ".join(sample_vals))
    if top:
        parts.append("Top values: " + " | ".join(f"{k} ({n})" for k, n in top))
    text = "\n".join(parts)
    return text[:8000]  # cap to keep DB size reasonable


def record_mapping_examples(
    import_obj: MouseImport,
    df: pd.DataFrame,
    *,
    user,
    mapping: dict[str, str],
) -> int:
    """
    Store supervised examples from the user's saved mapping.
    Returns number of examples created.
    Skips blanks/unmapped/fixed/nonexistent columns.
    """
    try:
        MouseImportMappingExample.objects.filter(mouse_import=import_obj).delete()
    except (OperationalError, ProgrammingError):
        return 0

    if not mapping:
        return 0

    cols = set(str(c) for c in df.columns)

    rows: list[MouseImportMappingExample] = []
    for target_field, selected in mapping.items():
        if selected is None:
            continue
        selected_str = str(selected).strip()

        if selected_str == "":
            continue
        if selected_str == "-- fixed --":
            continue
        if selected_str.lower() in {"none", "null", "n/a", "na"}:
            continue
        if selected_str not in cols:
            continue

        header = selected_str
        col_text = _build_column_text(header, df[header])

        rows.append(
            MouseImportMappingExample(
                mouse_import=import_obj,
                project=import_obj.project,
                created_by=user if getattr(user, "is_authenticated", False) else None,
                target_field=target_field,
                source_header=header,
                source_header_norm=_normalise_text(header)[:256],
                column_text=col_text,
            )
        )

    if not rows:
        return 0

    try:
        MouseImportMappingExample.objects.bulk_create(rows)
    except (OperationalError, ProgrammingError):
        return 0

    return len(rows)


def _load_model_bundle() -> dict[str, Any] | None:
    """
    Load trained bundle from DB if available. Safe when tables missing.
    """
    try:
        state = MouseImportMappingModelState.objects.filter(id=1).first()
    except (OperationalError, ProgrammingError):
        return None

    if not state or not state.model_blob:
        return None

    import joblib
    from io import BytesIO

    return joblib.load(BytesIO(state.model_blob))


@dataclass(frozen=True)
class Suggestion:
    column: str
    score: float


def suggest_mapping_for_dataframe(
    df: pd.DataFrame,
    project,
    *,
    optional_threshold: float = DEFAULT_OPTIONAL_THRESHOLD,
    top_k: int = 3,
) -> tuple[dict[str, str], dict[str, list[Suggestion]]]:
    """
    Returns:
      - initial dict for ColumnMappingForm: {"map_<field>": "<column>"}
      - debug suggestions per field
    """
    required, optional, _choices = get_mouse_import_targets(project)
    required_fields = [f for f, _ in required]
    optional_fields = [f for f, _ in optional]
    fields = required_fields + optional_fields
    columns = [str(c) for c in df.columns]

    if not fields or not columns:
        return {}, {}

    # Build column documents
    col_texts = [_build_column_text(c, df[c]) for c in columns]

    # Use trained model if present, else fallback to header similarity only
    bundle = _load_model_bundle()
    scores = [[0.0 for _ in columns] for _ in fields]

    if bundle is not None:
        vectorizer = bundle["vectorizer"]
        clf = bundle["clf"]
        classes = list(bundle["classes"])
        class_index = {c: i for i, c in enumerate(classes)}

        X = vectorizer.transform(col_texts)
        probs = clf.predict_proba(X)  # (C, n_classes)

        for fi, field_name in enumerate(fields):
            idx = class_index.get(field_name)
            for ci in range(len(columns)):
                base = float(probs[ci, idx]) if idx is not None else 0.0
                # small header boost
                field = Mouse._meta.get_field(field_name)
                verbose = str(getattr(field, "verbose_name", field_name))
                base += 0.15 * _header_similarity(columns[ci], field_name, verbose)
                scores[fi][ci] = min(1.0, base)
    else:
        for fi, field_name in enumerate(fields):
            field = Mouse._meta.get_field(field_name)
            verbose = str(getattr(field, "verbose_name", field_name))
            for ci, col in enumerate(columns):
                scores[fi][ci] = _header_similarity(col, field_name, verbose)

    suggestions: dict[str, list[Suggestion]] = {}
    for fi, field_name in enumerate(fields):
        ranked = sorted(
            [
                Suggestion(column=columns[ci], score=float(scores[fi][ci]))
                for ci in range(len(columns))
            ],
            key=lambda s: s.score,
            reverse=True,
        )
        suggestions[field_name] = ranked[: max(1, top_k)]

    # Greedy one-to-one assignment (required first)
    assigned: dict[str, str] = {}
    used_cols: set[str] = set()

    pairs: list[tuple[int, float, str, str]] = []
    for fi, field_name in enumerate(fields):
        is_req = 1 if field_name in required_fields else 0
        for ci, col in enumerate(columns):
            pairs.append((is_req, float(scores[fi][ci]), field_name, col))

    pairs.sort(key=lambda t: (t[0], t[1]), reverse=True)

    for is_req, score, field_name, col in pairs:
        if field_name in assigned:
            continue
        if col in used_cols:
            continue
        if field_name in optional_fields and score < optional_threshold:
            continue
        assigned[field_name] = col
        used_cols.add(col)

    for f in required_fields:
        if f not in assigned and suggestions.get(f):
            assigned[f] = suggestions[f][0].column

    initial = {f"map_{f}": assigned.get(f, "") for f in fields}
    return initial, suggestions
