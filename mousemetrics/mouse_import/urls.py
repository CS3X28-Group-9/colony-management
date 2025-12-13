from django.urls import path
from . import views

app_name = "mouse_import"

urlpatterns = [
    path("import/", views.import_form, name="import_form"),
    path("import/<int:id>/preview/", views.import_preview, name="import_preview"),
    path("import/<int:id>/commit/", views.import_commit, name="import_commit"),
]
