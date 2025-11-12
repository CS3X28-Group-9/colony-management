from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "mouseapp"

urlpatterns = [
    path("", views.home, name="home"),
    path("mouse/<int:id>/", views.mouse, name="mouse"),
    path("project/<int:id>/", views.project, name="project"),
    path("register/", views.register, name="register"),
    path("family_tree/<int:mouse>/", views.family_tree, name="family_tree"),
    path("requests/", views.requests_list, name="requests"),
    path(
        "requests/breeding/create/",
        views.create_breeding_request,
        name="create_breeding_request",
    ),
    path(
        "requests/culling/create/",
        views.create_culling_request,
        name="create_culling_request",
    ),
    path(
        "requests/transfer/create/",
        views.create_transfer_request,
        name="create_transfer_request",
    ),
    path(
        "requests/<int:request_id>/update-status/",
        views.update_request_status,
        name="update_request_status",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
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
