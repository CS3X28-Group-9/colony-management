from django.db import models
from django.contrib.auth import get_user_model


class MouseImport(models.Model):
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
    original_filename = models.CharField(
        max_length=255,
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
