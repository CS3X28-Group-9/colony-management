from __future__ import annotations

from io import BytesIO

from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from mouse_import.models import MouseImportMappingExample, MouseImportMappingModelState


def maybe_train_mapping_model(*, min_new_examples: int = 10) -> str:
    """
    Train when >=min_new_examples new examples exist since last training.

    This is called synchronously after saving mappings.
    Uses a DB lock on the singleton state row to avoid concurrent training.
    """
    try:
        latest = MouseImportMappingExample.objects.order_by("-id").first()
    except (OperationalError, ProgrammingError):
        return "Skipped (training tables not ready)."

    if not latest:
        return "Skipped (no training data)."

    # Acquire lock on singleton state row
    with transaction.atomic():
        state, _ = (
            MouseImportMappingModelState.objects.select_for_update().get_or_create(id=1)
        )

        if state.training_in_progress:
            return "Skipped (training already in progress)."

        new_count = int(latest.id) - int(state.trained_up_to_example_id or 0)
        if new_count < min_new_examples:
            return f"Skipped ({new_count} new examples; threshold {min_new_examples})."

        # Mark in-progress and release lock (unblocks other operations)
        state.training_in_progress = True
        state.save(update_fields=["training_in_progress", "updated_at"])

    # Train outside the lock/transaction
    try:
        qs = MouseImportMappingExample.objects.order_by("id")
        texts = [e.column_text for e in qs if e.column_text]
        labels = [e.target_field for e in qs if e.column_text]
        if len(set(labels)) < 2:
            _finish_training(latest_id=int(latest.id), n_examples=len(texts), blob=None)
            return "Skipped (need >=2 classes)."

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        import joblib

        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            max_features=40000,
        )
        X = vectorizer.fit_transform(texts)

        clf = LogisticRegression(
            max_iter=2000,
            solver="lbfgs",
            class_weight="balanced",
        )
        clf.fit(X, labels)

        bundle = {
            "vectorizer": vectorizer,
            "clf": clf,
            "classes": list(clf.classes_),
        }

        buf = BytesIO()
        joblib.dump(bundle, buf)
        blob = buf.getvalue()

        _finish_training(latest_id=int(latest.id), n_examples=len(texts), blob=blob)
        return f"Trained model on {len(texts)} examples (up to id={latest.id})."
    except Exception as exc:
        # clear training_in_progress even on failure
        _finish_training(latest_id=None, n_examples=None, blob=None, clear_only=True)
        return f"Training failed: {exc}"


def _finish_training(
    *,
    latest_id: int | None,
    n_examples: int | None,
    blob: bytes | None,
    clear_only: bool = False,
) -> None:
    with transaction.atomic():
        state, _ = (
            MouseImportMappingModelState.objects.select_for_update().get_or_create(id=1)
        )
        state.training_in_progress = False

        if not clear_only and latest_id is not None and n_examples is not None:
            state.trained_up_to_example_id = latest_id
            state.n_examples = n_examples
            state.model_blob = blob

        state.save()
