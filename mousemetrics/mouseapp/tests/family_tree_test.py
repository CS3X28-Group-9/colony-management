from datetime import date

import pytest
from django.urls import reverse

from mouseapp.models import Mouse, Box, Project, Strain


def s(n):
    return Strain.objects.get_or_create(name=n)[0]


@pytest.fixture
def mice(db):
    """
    Creates a small family tree fixture for testing.
    """
    box = Box(number="0")
    project = Project(name="Test Project", start_date=date(2000, 1, 1))
    kwargs = dict(
        date_of_birth=date(1970, 1, 1),
        tube_number=0,
        box=box,
        project=project,
        coat_colour="Black",
        notes=".",
    )
    box.save()
    project.save()

    # Create the family structure
    grandfather = Mouse(strain=s("M'"), sex="M", **kwargs)
    father = Mouse(strain=s("M"), sex="M", father=grandfather, **kwargs)
    mother = Mouse(strain=s("F"), sex="F", **kwargs)
    ref = Mouse(
        strain=s("MF"),
        sex="F",
        mother=mother,
        father=father,
        **kwargs,
    )
    child = Mouse(strain=s("MF."), sex="M", mother=ref, **kwargs)

    mice_list = (grandfather, father, mother, ref, child)
    for mouse in mice_list:
        mouse.save()

    return mice_list


@pytest.mark.django_db
def test_missing_mouse(client):
    """
    Ensure the view returns 404 if the mouse ID doesn't exist.
    """
    response = client.get(reverse("mouseapp:family_tree", args=[404]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_render_tree(client, mice):
    """
    Ensure the SVG family tree page loads successfully (Status 200).
    Checks that the response contains an SVG tag.
    """
    (_, _, _, ref, _) = mice
    response = client.get(reverse("mouseapp:family_tree", args=[ref.id]))

    assert response.status_code == 200
    assert "<svg" in response.content.decode()
