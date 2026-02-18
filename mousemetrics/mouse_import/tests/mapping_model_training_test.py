# mousemetrics/mouse_import/tests/mapping_model_training_test.py
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
from mouse_import.services.mapping_train import maybe_train_mapping_model
from mouseapp.models import Project


@pytest.fixture
def project(db):
    return Project.objects.create(
        name="P",
        start_date="2000-01-01",
        license_constraints="",
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
    MouseImportMappingModelState.objects.get_or_create(id=1)

    _seed_examples(project, import_obj, n_pairs=3)  # 9 examples
    msg = maybe_train_mapping_model(min_new_examples=10)
    assert msg.startswith("Skipped")

    _seed_examples(project, import_obj, n_pairs=1)  # +3 => 12
    msg = maybe_train_mapping_model(min_new_examples=10)
    assert msg.startswith("Trained")

    state = MouseImportMappingModelState.objects.get(id=1)
    assert state.model_blob is not None
    assert state.training_in_progress is False
    assert state.trained_up_to_example_id > 0


def test_suggestions_use_trained_model(db, project, import_obj):
    MouseImportMappingModelState.objects.get_or_create(id=1)
    _seed_examples(project, import_obj, n_pairs=4)  # 12 examples
    msg = maybe_train_mapping_model(min_new_examples=10)
    assert msg.startswith("Trained")

    df = pd.DataFrame(
        [
            {"Tube ID": "1", "DOB": "1970-01-01", "Sex": "M"},
            {"Tube ID": "2", "DOB": "1970-01-02", "Sex": "F"},
        ]
    )

    initial, _debug = suggest_mapping_for_dataframe(df, project)

    assert initial.get("map_tube_number") == "Tube ID"
    assert initial.get("map_date_of_birth") == "DOB"
    if "map_sex" in initial:
        assert initial.get("map_sex") == "Sex"
