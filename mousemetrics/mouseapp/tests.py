import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_renders_template(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


@pytest.mark.django_db
def test_index_gives_correct_content_type(client):
    response = client.get(reverse("home"))
    assert response["Content-Type"] == "text/html; charset=utf-8"
