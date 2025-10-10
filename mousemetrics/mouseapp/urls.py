from django.urls import path, include
from .views import home, register

urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("register/", register, name="register"),
]
