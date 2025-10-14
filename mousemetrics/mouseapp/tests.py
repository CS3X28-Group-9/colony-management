import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from .forms import RegistrationForm

User = get_user_model()


@pytest.mark.django_db
def test_home_renders_template(client):
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
    assert db_user.email == user_data["email"]
    assert db_user.first_name == user_data["first_name"]
    assert db_user.last_name == user_data["last_name"]
    assert db_user.check_password(user_data["password1"])
