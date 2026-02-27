from io import BytesIO

from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError

from mouse_import.models import MouseImportMappingExample, MouseImportMappingModelState

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# could have this in a sepeerate module if we add more mapping-related services, but for now it can live here with the training logic
class TrainStatus(str, Enum):
    SKIPPED = "skipped"
    TRAINED = "trained"
    FAILED = "failed"


class SkipReason(str, Enum):
    TABLES_NOT_READY = "tables_not_ready"
    NO_TRAINING_DATA = "no_training_data"
    IN_PROGRESS = "in_progress"
    BELOW_THRESHOLD = "below_threshold"
    NEED_2_CLASSES = "need_2_classes"


@dataclass(frozen=True)
class TrainOutcome:
    status: TrainStatus
    skip_reason: Optional[SkipReason] = None

    # useful metadata
    latest_id: Optional[int] = None
    n_examples: Optional[int] = None
    new_examples: Optional[int] = None
    threshold: Optional[int] = None

    # for failures
    error: Optional[str] = None

    def user_message(self) -> Optional[str]:
        """Only return something we actually want to show in the UI."""
        if self.status == TrainStatus.TRAINED:
            return f"Trained model on {self.n_examples} examples (up to id={self.latest_id})."
        if self.status == TrainStatus.FAILED:
            return f"Training failed: {self.error}"
        return None


def maybe_train_mapping_model(*, min_new_examples: int = 10) -> TrainOutcome:
    """
    Train when >=min_new_examples new examples exist since last training.

    This is called synchronously after saving mappings.
    Uses a DB lock on the singleton state row to avoid concurrent training.
    """
    try:
        latest = MouseImportMappingExample.objects.order_by("-id").first()
    except (OperationalError, ProgrammingError):
        return TrainOutcome(
            status=TrainStatus.SKIPPED,
            skip_reason=SkipReason.TABLES_NOT_READY,
        )

    if not latest:
        return TrainOutcome(
            status=TrainStatus.SKIPPED,
            skip_reason=SkipReason.NO_TRAINING_DATA,
        )

    # Acquire lock on singleton state row
    with transaction.atomic():
        state, _ = (
            MouseImportMappingModelState.objects.select_for_update().get_or_create(id=1)
        )

        if state.training_in_progress:
            return TrainOutcome(
                status=TrainStatus.SKIPPED,
                skip_reason=SkipReason.IN_PROGRESS,
                latest_id=int(latest.id),
            )

        new_count = int(latest.id) - int(state.trained_up_to_example_id or 0)
        if new_count < min_new_examples:
            return TrainOutcome(
                status=TrainStatus.SKIPPED,
                skip_reason=SkipReason.BELOW_THRESHOLD,
                latest_id=int(latest.id),
                new_examples=new_count,
                threshold=min_new_examples,
            )

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
            return TrainOutcome(
                status=TrainStatus.SKIPPED,
                skip_reason=SkipReason.NEED_2_CLASSES,
                latest_id=int(latest.id),
                n_examples=len(texts),
            )

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

        bundle = {"vectorizer": vectorizer, "clf": clf, "classes": list(clf.classes_)}

        buf = BytesIO()
        joblib.dump(bundle, buf)
        blob = buf.getvalue()

        _finish_training(latest_id=int(latest.id), n_examples=len(texts), blob=blob)

        return TrainOutcome(
            status=TrainStatus.TRAINED,
            latest_id=int(latest.id),
            n_examples=len(texts),
        )

    except Exception as exc:
        # clear training_in_progress even on failure
        _finish_training(latest_id=None, n_examples=None, blob=None, clear_only=True)
        return TrainOutcome(
            status=TrainStatus.FAILED,
            latest_id=int(latest.id),
            error=str(exc),
        )


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
