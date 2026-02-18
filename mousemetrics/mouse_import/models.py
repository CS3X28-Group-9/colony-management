from django.db import models
from django.contrib.auth import get_user_model


class MouseImport(models.Model):
    id: int
    uploaded_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who uploaded the file.",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    project = models.ForeignKey(
        "mouseapp.Project",
        on_delete=models.PROTECT,
        related_name="mouse_imports",
        help_text="Project that owns the imported mice.",
    )
    file = models.FileField(
        upload_to="mouse_imports/",
        help_text="Stored under MEDIA_ROOT/mouse_imports/.",
    )
    original_filename = models.TextField(
        blank=True,
        help_text="Original name of the uploaded file.",
    )
    sheet_name = models.CharField(
        max_length=128,
        blank=True,
        help_text="Leave blank to use the active worksheet.",
    )
    cell_range = models.CharField(
        max_length=32,
        help_text='Excel range such as "A1:M40".',
    )

    row_count = models.IntegerField(default=0)
    committed = models.BooleanField(default=False, db_index=True)
    error_log = models.TextField(
        blank=True,
        help_text="Captures validation or commit warnings.",
    )

    class Meta:
        ordering = ["-uploaded_at"]


class MouseImportMappingExample(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouse_import_mapping_examples",
    )
    project = models.ForeignKey(
        "mouseapp.Project",
        on_delete=models.PROTECT,
        related_name="mouse_import_mapping_examples",
        db_index=True,
    )
    mouse_import = models.ForeignKey(
        "mouse_import.MouseImport",
        on_delete=models.CASCADE,
        related_name="mapping_examples",
    )

    target_field = models.CharField(max_length=128, db_index=True)
    source_header = models.TextField()
    source_header_norm = models.CharField(max_length=256, db_index=True)

    # Header + samples + top values
    column_text = models.TextField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_header_norm", "target_field"]),
            models.Index(fields=["project", "target_field"]),
        ]


class MouseImportMappingModelState(models.Model):
    """
    Singleton state row (id=1) used to:
      - decide when to retrain
      - store the trained model bundle in DB
      - prevent concurrent training
    """

    # Force singleton usage by convention (id=1)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    trained_up_to_example_id = models.BigIntegerField(default=0)
    n_examples = models.IntegerField(default=0)

    training_in_progress = models.BooleanField(default=False, db_index=True)

    # Joblib blob containing: {"vectorizer": ..., "clf": ..., "classes": ...}
    model_blob = models.BinaryField(null=True, blank=True)

    class Meta:
        verbose_name = "Mouse Import Mapping Model State"
