import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from .forms import RegistrationForm


@pytest.mark.django_db
def test_home_renders_template(client: Client):
    response = client.get(reverse("mouseapp:home"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.django_db
def test_user_creation():
    user_data = {
        "email": "test@abdn.ac.uk",
        "first_name": "T",
        "last_name": "E",
        "password1": "Str0ngPass123!",
        "password2": "Str0ngPass123!",
    }

    form = RegistrationForm(data=user_data)
    assert form.is_valid()

    user = form.save()
    assert user is not None

    db_user = User.objects.get(email=user_data["email"])
    assert db_user.email == user_data["email"]  # type: ignore reportUnknownArgumentType
    assert db_user.first_name == user_data["first_name"]  # type: ignore reportUnknownMemberType
    assert db_user.last_name == user_data["last_name"]  # type: ignore reportUnknownMemberType
    assert db_user.check_password(user_data["password1"])  # type: ignore reportUnknownMemberType


@pytest.mark.django_db
def test_registration_redirect(client: Client):
    register_url = reverse("mouseapp:register")
    login_url = reverse("mouseapp:login")
    user_data = {
        "email": "redirect_test@abdn.ac.uk",
        "first_name": "Redirect",
        "last_name": "Test",
        "password1": "a-secure-password",
        "password2": "a-secure-password",
    }

    response = client.post(register_url, data=user_data)
    assert response.status_code == 302, "Expected a redirect after registration"
    assert (
        response.url == login_url  # pyright: ignore
    ), f"Expected redirect to {login_url}, but got {response.url}"  # pyright: ignore


@pytest.mark.django_db
def test_login_redirect(client: Client):
    login_url = reverse("mouseapp:login")
    home_url = reverse("mouseapp:home")
    password = "a-very-secure-password"
    user: User = User.objects.create_user(
        username="loginuser@example.com",
        email="loginuser@example.com",
        password=password,
        first_name="Login",
        last_name="User",
    )

    response = client.post(
        login_url,
        {
            "username": user.email,  # pyright: ignore reportUnknownMemberType
            "password": password,  # pyright: ignore reportUnknownMemberType
        },
    )

    assert response.status_code == 302, "Expected a redirect after login"
    assert (
        response.url == home_url  # pyright: ignore
    ), f"Expected redirect to {home_url}, but got {response.url}"  # pyright: ignore


@pytest.mark.django_db
def test_local_email_normalisation():
    user_data = {
        "email": "loginuser@example.com",
        "first_name": "T",
        "last_name": "E",
        "password1": "Str0ngPass123!",
        "password2": "Str0ngPass123!",
    }
    user1 = RegistrationForm(data=user_data)
    assert user1.is_valid(), user1.errors
    user1.save()

    user_data2 = {
        "email": "LOGINUSER@example.com",
        "first_name": "T",
        "last_name": "E",
        "password1": "Str0ngPass123!",
        "password2": "Str0ngPass123!",
    }
    user2 = RegistrationForm(data=user_data2)
    assert user2.is_valid(), user2.errors
    user2.save()

    assert User.objects.filter(email="loginuser@example.com").exists()
    assert User.objects.filter(email="LOGINUSER@example.com").exists()

    user_data3 = {
        "email": "LOGINUSER@example.com",
        "first_name": "T",
        "last_name": "E",
        "password1": "Str0ngPass123!",
        "password2": "Str0ngPass123!",
    }

    user3 = RegistrationForm(data=user_data3)
    assert not user3.is_valid(), user3.errors
    assert user3.errors is not None
    assert "This email is already registered." in user3.errors["email"]
