from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("mouse_import", "0003_alter_mouseimport_original_filename"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mouseapp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MouseImportMappingExample",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("target_field", models.CharField(db_index=True, max_length=128)),
                ("source_header", models.TextField()),
                ("source_header_norm", models.CharField(db_index=True, max_length=256)),
                ("column_text", models.TextField()),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mouse_import_mapping_examples",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mouse_import_mapping_examples",
                        to="mouseapp.project",
                    ),
                ),
                (
                    "mouse_import",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mapping_examples",
                        to="mouse_import.mouseimport",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="mouseimportmappingexample",
            index=models.Index(
                fields=["source_header_norm", "target_field"],
                name="mi_mapex_hdrfld_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="mouseimportmappingexample",
            index=models.Index(
                fields=["project", "target_field"], name="mi_mapex_projfld_idx"
            ),
        ),
        migrations.CreateModel(
            name="MouseImportMappingModelState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("trained_up_to_example_id", models.BigIntegerField(default=0)),
                ("n_examples", models.IntegerField(default=0)),
                (
                    "training_in_progress",
                    models.BooleanField(db_index=True, default=False),
                ),
                ("model_blob", models.BinaryField(blank=True, null=True)),
            ],
            options={"verbose_name": "Mouse Import Mapping Model State"},
        ),
    ]
