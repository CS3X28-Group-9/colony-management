from django.urls import path, include
from . import views

app_name = "mouseapp"  # namespacing the app

urlpatterns = [
    path("", views.home, name="home"),
    path("mouse/<int:id>/", views.mouse, name="mouse"),
    path("project/<int:id>/", views.project, name="project"),
    path("register/", views.register, name="register"),
    path(
        "registration/", include("django.contrib.auth.urls")
    ),  # includes login, logout, password management URLs
]
