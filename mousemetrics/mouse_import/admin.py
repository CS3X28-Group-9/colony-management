from django.contrib import admin
from .models import MouseImport


@admin.register(MouseImport)
class MouseImportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "uploaded_by",
        "project",
        "uploaded_at",
        "committed",
        "row_count",
        "original_filename",
    )
    list_filter = ("committed", "project", "uploaded_at")
    search_fields = ("original_filename", "file")
    readonly_fields = ("uploaded_at",)
