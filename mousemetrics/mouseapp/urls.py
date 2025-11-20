from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "mouseapp"

urlpatterns = [
    # ========================
    # Core app views
    # ========================
    path("", views.home, name="home"),
    path("mouse/<int:id>/", views.mouse, name="mouse"),
    path("mouse/<int:id>/edit/", views.edit_mouse, name="edit_mouse"),
    path("project/<int:id>/", views.project, name="project"),
    path("project/<int:id>/edit/", views.edit_project, name="edit_project"),
    path("project/<int:id>/invite-member/", views.invite_member, name="invite_member"),
    path("project/<int:id>/remove-member/", views.remove_member, name="remove_member"),
    path("register/", views.register, name="register"),
    path("family_tree/<int:mouse>/", views.family_tree, name="family_tree"),
    # ========================
    # Authentication routes
    # ========================
    # Using Django’s built-in auth views but pointing to our custom templates in /templates/accounts/
    path(
        "login/",
        views.login_view,
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="mouseapp:home"),
        name="logout",
    ),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("mouseapp:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("mouseapp:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
