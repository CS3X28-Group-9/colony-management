import pytest
import pandas as pd

from mouse_import.models import (
    MouseImport,
    MouseImportMappingExample,
    MouseImportMappingModelState,
)
from mouse_import.services.mapping_ai import (
    record_mapping_examples,
    suggest_mapping_for_dataframe,
)
from mouse_import.services.mapping_train import (
    maybe_train_mapping_model,
    TrainStatus,
    SkipReason,
)


@pytest.fixture
def import_obj(db, django_user_model, project):
    user = django_user_model.objects.create_user(username="importer", password="x")
    return MouseImport.objects.create(
        uploaded_by=user,
        project=project,
        file="mouse_imports/dummy.csv",
        original_filename="dummy.csv",
        sheet_name="",
        cell_range="A1:J3",
    )


def test_record_mapping_examples_only_real_columns(db, import_obj, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="x")

    df = pd.DataFrame(
        [
            {"Tube ID": "1", "DOB": "1970-01-01", "Sex": "M", "Notes": ""},
            {"Tube ID": "2", "DOB": "1970-01-02", "Sex": "F", "Notes": ""},
        ]
    )

    mapping = {
        "tube_number": "Tube ID",
        "date_of_birth": "DOB",
        "sex": "Sex",
        "notes": "",  # unmapped -> skip
        "strain": "-- fixed --",  # fixed -> skip
        "box": "Missing Col",  # not in df.columns -> skip
    }

    n = record_mapping_examples(import_obj, df, user=user, mapping=mapping)
    assert n == 3
    assert MouseImportMappingExample.objects.count() == 3


def _seed_examples(project, import_obj, n_pairs: int):
    """
    Each pair adds 3 examples (tube_number, date_of_birth, sex).
    """
    rows = []
    for _ in range(n_pairs):
        rows.append(
            MouseImportMappingExample(
                project=project,
                mouse_import=import_obj,
                created_by=None,
                target_field="tube_number",
                source_header="Tube ID",
                source_header_norm="tube id",
                column_text="Header: Tube ID\nExamples: 1 | 2 | 3\nTop values: 1 (1)",
            )
        )
        rows.append(
            MouseImportMappingExample(
                project=project,
                mouse_import=import_obj,
                created_by=None,
                target_field="date_of_birth",
                source_header="DOB",
                source_header_norm="dob",
                column_text="Header: DOB\nExamples: 1970-01-01 | 1970-01-02",
            )
        )
        rows.append(
            MouseImportMappingExample(
                project=project,
                mouse_import=import_obj,
                created_by=None,
                target_field="sex",
                source_header="Sex",
                source_header_norm="sex",
                column_text="Header: Sex\nExamples: M | F | M",
            )
        )

    MouseImportMappingExample.objects.bulk_create(rows)


def test_training_triggers_every_10_new_examples(db, project, import_obj):
    # Ensure singleton exists (not strictly required because training creates it, but nice for clarity)
    MouseImportMappingModelState.objects.get_or_create(id=1)

    _seed_examples(project, import_obj, n_pairs=3)  # 9 examples
    out = maybe_train_mapping_model(min_new_examples=10)
    assert out.status == TrainStatus.SKIPPED
    assert out.skip_reason == SkipReason.BELOW_THRESHOLD
    assert out.new_examples == 9
    assert out.threshold == 10
    assert out.latest_id is not None

    _seed_examples(
        project, import_obj, n_pairs=1
    )  # +3 => 12 examples total since trained_up_to_example_id=0
    out = maybe_train_mapping_model(min_new_examples=10)
    assert out.status == TrainStatus.TRAINED
    assert out.latest_id is not None
    assert out.n_examples is not None
    assert out.n_examples >= 12

    state = MouseImportMappingModelState.objects.get(id=1)
    assert state.model_blob is not None
    assert state.training_in_progress is False
    assert state.trained_up_to_example_id == out.latest_id
    assert state.n_examples == out.n_examples


def test_training_skips_need_two_classes(db, project, import_obj):
    """
    If all examples are the same target_field, training should skip with NEED_2_CLASSES
    and still clear training_in_progress + advance trained_up_to_example_id.
    """
    MouseImportMappingModelState.objects.get_or_create(id=1)

    rows = [
        MouseImportMappingExample(
            project=project,
            mouse_import=import_obj,
            created_by=None,
            target_field="tube_number",
            source_header="Tube ID",
            source_header_norm="tube id",
            column_text="Header: Tube ID\nExamples: 1 | 2 | 3",
        )
        for _ in range(12)
    ]
    MouseImportMappingExample.objects.bulk_create(rows)

    out = maybe_train_mapping_model(min_new_examples=10)
    assert out.status == TrainStatus.SKIPPED
    assert out.skip_reason == SkipReason.NEED_2_CLASSES
    assert out.latest_id is not None
    assert out.n_examples == 12

    state = MouseImportMappingModelState.objects.get(id=1)
    assert state.training_in_progress is False
    # blob is expected to be None in this case (your code passes blob=None)
    assert state.model_blob is None
    assert state.trained_up_to_example_id == out.latest_id
    assert state.n_examples == 12


def test_suggestions_use_trained_model(db, project, import_obj):
    MouseImportMappingModelState.objects.get_or_create(id=1)
    _seed_examples(project, import_obj, n_pairs=4)  # 12 examples
    out = maybe_train_mapping_model(min_new_examples=10)
    assert out.status == TrainStatus.TRAINED

    df = pd.DataFrame(
        [
            {"Tube ID": "1", "DOB": "1970-01-01", "Sex": "M"},
            {"Tube ID": "2", "DOB": "1970-01-02", "Sex": "F"},
        ]
    )

    initial, _debug = suggest_mapping_for_dataframe(df, project)

    assert initial.get("map_tube_number") == "Tube ID"
    assert initial.get("map_date_of_birth") == "DOB"
    assert initial.get("map_sex") == "Sex"


def test_training_in_progress_short_circuits(db, project, import_obj):
    """
    If training_in_progress is already True, we should short-circuit with IN_PROGRESS.
    """
    state, _ = MouseImportMappingModelState.objects.get_or_create(id=1)
    state.training_in_progress = True
    state.save(update_fields=["training_in_progress"])

    _seed_examples(project, import_obj, n_pairs=4)  # 12 examples exist
    out = maybe_train_mapping_model(min_new_examples=10)
    assert out.status == TrainStatus.SKIPPED
    assert out.skip_reason == SkipReason.IN_PROGRESS
