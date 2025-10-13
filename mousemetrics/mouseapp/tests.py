import pytest
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from .forms import RegistrationForm

User = get_user_model()


@pytest.mark.django_db
def test_home_renders_template(client):
    response = client.get(reverse("mouseapp:home"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html; charset=utf-8"


class RegistrationTest(TestCase):
    def test_user_creation(self):
        user_data = {
            "email": "test@abdn.ac.uk",
            "first_name": "T",
            "last_name": "E",
            "password1": "Str0ngPass123!",
            "password2": "Str0ngPass123!",
        }

        form = RegistrationForm(data=user_data)
        self.assertTrue(form.is_valid())

        user = form.save()
        self.assertIsNotNone(user)

        try:
            db_user = User.objects.get(email=user_data["email"])
            self.assertEqual(db_user.email, user_data["email"])
            self.assertEqual(db_user.first_name, user_data["first_name"])
            self.assertEqual(db_user.last_name, user_data["last_name"])
            self.assertTrue(db_user.check_password(user_data["password1"]))

        except User.DoesNotExist:
            self.fail("User was not found in the database after registration.")
