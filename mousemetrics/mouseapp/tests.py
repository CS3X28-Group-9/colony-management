import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_index_gives_correct_message(client):
    response = client.get(reverse("mouseapp-hello"))
    assert response.status_code == 200
    assert response.content.decode() == "Hello, world. You're at the mouseapp index."


@pytest.mark.django_db
def test_index_gives_correct_content_type(client):
    response = client.get(reverse("mouseapp-hello"))
    assert response["Content-Type"] == "text/html; charset=utf-8"
