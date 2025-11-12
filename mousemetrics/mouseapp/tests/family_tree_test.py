from datetime import date

import pytest
from django.urls import reverse

from mouseapp.models import Mouse, Box, Project, Strain
from mouseapp.views import family_tree_ancestry


def s(n):
    return Strain.objects.get_or_create(name=n)[0]


@pytest.fixture
def mice(db):
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

    mice = (grandfather, father, mother, ref, child)
    for mouse in mice:
        mouse.save()

    return mice


@pytest.mark.django_db
def test_missing_mouse(client):
    response = client.get(reverse("mouseapp:family_tree", args=[404]))
    assert response.status_code == 404


def test_layout_ancestry(mice):
    (grandfather, father, mother, ref, child) = mice
    layout = family_tree_ancestry(child)

    assert layout == [
        [None, None, None, None, grandfather, None, None, None],
        [None, None, father, mother],
        [None, ref],
        [child],
    ]


def test_render_tree(client, mice):
    (_, _, _, ref, _) = mice
    response = client.get(reverse("mouseapp:family_tree", args=[ref.id]))
    assert response.status_code == 200
