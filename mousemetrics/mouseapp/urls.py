from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = "mouseapp"

urlpatterns = [
    path("", views.home, name="home"),
    path("mouse/<int:id>/", views.mouse, name="mouse"),
    path("project/<int:id>/", views.project, name="project"),
    path(
        "accounts/register/",
        views.register,
        name="register",
    ),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
]
