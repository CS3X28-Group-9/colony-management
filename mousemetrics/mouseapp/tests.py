import pytest
from django.urls import reverse
from django.test import TestCase
from .forms import RegistrationForm


@pytest.mark.django_db
def test_home_renders_template(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


class RegistrationTest(TestCase):
    def test_user_creation(self):
        form = RegistrationForm(
            data={
                "email": "test@abdn.ac.uk",
                "first_name": "T",
                "last_name": "E",
                "password1": "Str0ngPass123!",
                "password2": "Str0ngPass123!",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.save())
