from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "mouseapp"  # namespacing the app

urlpatterns = [
    # ========================
    # Core app views
    # ========================
    path("", views.home, name="home"),
    path("mouse/<int:id>/", views.mouse, name="mouse"),
    path("project/<int:id>/", views.project, name="project"),
    path("register/", views.register, name="register"),
    # ========================
    # Authentication routes
    # ========================
    # (keeps the simple built-in ones under /registration/)
    path("registration/", include("django.contrib.auth.urls")),
    # Optional explicit versions for more control (styling, templates, etc.)
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="mouseapp:home"),
        name="logout",
    ),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="auth/password_reset.html",
            email_template_name="auth/password_reset_email.html",
            subject_template_name="auth/password_reset_subject.txt",
            success_url=reverse_lazy("mouseapp:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html",
            success_url=reverse_lazy("mouseapp:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
