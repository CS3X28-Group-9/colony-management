from datetime import date
import pytest
from django.urls import reverse
from mouseapp.models import Mouse, Box, Project, Strain


def s(n):
    return Strain.objects.get_or_create(name=n)[0]


@pytest.fixture
def mice(db):
    box = Box(number="0")
    project = Project(name="Test Project", start_date=date(2000, 1, 1))

    box.save()
    project.save()

    kwargs = dict(
        date_of_birth=date(1970, 1, 1),
        tube_number=0,
        box=box,
        project=project,
        coat_colour="Black",
        notes=".",
    )

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
def test_missing_mouse(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="testuser",
        password="password",  # pragma: allowlist secret
    )
    client.force_login(user)

    response = client.get(reverse("mouseapp:family_tree", args=[404]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_render_container(client, mice, django_user_model):
    (_, _, _, ref, _) = mice

    user = django_user_model.objects.create_user(
        username="testuser_cont",
        password="password",  # pragma: allowlist secret
    )
    ref.project.researchers.add(user)
    client.force_login(user)

    response = client.get(reverse("mouseapp:family_tree", args=[ref.id]))

    assert response.status_code == 200
    expected_url = reverse("mouseapp:family_tree_svg", args=[ref.id])
    assert expected_url in response.content.decode()


@pytest.mark.django_db
def test_render_svg_image(client, mice, django_user_model):
    (_, _, _, ref, _) = mice

    user = django_user_model.objects.create_user(
        username="testuser_svg",
        password="password",  # pragma: allowlist secret
    )
    ref.project.researchers.add(user)
    client.force_login(user)

    response = client.get(reverse("mouseapp:family_tree_svg", args=[ref.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert "<svg" in response.content.decode()
