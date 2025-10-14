from django.urls import path, include
from .views import home, register

app_name = "mouseapp"  # namespacing the app

urlpatterns = [
    path("", home, name="home"),
    path("register/", register, name="register"),
    path(
        "registration/", include("django.contrib.auth.urls")
    ),  # includes login, logout, password management URLs
]
