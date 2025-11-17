import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from .forms import RegistrationForm
from .models import Strain


def ensure_strain(name: str = "C57BL/6") -> Strain:
    strain, _ = Strain.objects.get_or_create(name=name)
    return strain


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


@pytest.mark.django_db
def test_create_breeding_request_requires_login(client: Client):
    """Test that creating a request requires authentication."""
    url = reverse("mouseapp:create_breeding_request")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url.lower()  # pyright: ignore


@pytest.mark.django_db
def test_create_request(client: Client):
    """Test creating a breeding request."""
    from .models import Request, Mouse, Project, Box, Membership
    from django.contrib.auth.models import User

    user = User.objects.create_user(
        username="requester@example.com",
        email="requester@example.com",
        password="password123",
    )
    client.force_login(user)

    project = Project.objects.create(
        name="Test Project",
        start_date="2024-01-01",
        license_constraints="Test constraints",
    )
    Membership.objects.create(project=project, user=user)
    box = Box.objects.create(
        number="1",
        location="E",
        box_type="S",
        project=project,
    )
    mouse = Mouse.objects.create(
        project=project,
        sex="M",
        date_of_birth="2024-01-01",
        tube_number=1,
        box=box,
        strain=ensure_strain(),
    )

    url = reverse("mouseapp:create_breeding_request")
    response = client.post(
        url,
        {
            "mouse": mouse.pk,
            "kind": "B",
            "details": "Test breeding request",
        },
    )

    assert response.status_code == 302
    assert Request.objects.filter(creator=user, kind="B").exists()
    request_obj = Request.objects.get(creator=user, kind="B")
    assert request_obj.mouse == mouse
    assert request_obj.status == "pending"
    assert request_obj.details == "Test breeding request"


@pytest.mark.django_db
def test_request_status_change_permissions(client: Client):
    """Test that only authorized users can change request status."""
    from .models import Request, Mouse, Project, Box
    from django.contrib.auth.models import User

    regular_user = User.objects.create_user(
        username="regular@example.com",
        email="regular@example.com",
        password="password123",
    )
    admin_user = User.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="password123",
        is_superuser=True,
    )

    project = Project.objects.create(
        name="Test Project",
        start_date="2024-01-01",
        license_constraints="Test constraints",
        lead=admin_user,
    )
    box = Box.objects.create(
        number="1",
        location="E",
        box_type="S",
        project=project,
    )
    mouse = Mouse.objects.create(
        project=project,
        sex="M",
        date_of_birth="2024-01-01",
        tube_number=1,
        box=box,
        strain=ensure_strain(),
    )

    request_obj = Request.objects.create(
        creator=regular_user,
        mouse=mouse,
        project=project,
        kind="B",
        details="Test request",
        status="pending",
    )

    client.force_login(regular_user)
    url = reverse("mouseapp:update_request_status", args=[request_obj.pk])
    response = client.post(url, {"status": "accepted"})
    assert response.status_code == 403

    client.force_login(admin_user)
    response = client.post(url, {"status": "accepted"})
    assert response.status_code == 302
    request_obj.refresh_from_db()
    assert request_obj.status == "accepted"


@pytest.mark.django_db
def test_request_status_change_requires_mouse_project_access(client: Client):
    """Test that users cannot change request status without mouse/project access."""
    from .models import Request, Mouse, Project, Box, Membership
    from django.contrib.auth.models import User, Permission
    from django.contrib.contenttypes.models import ContentType

    requester = User.objects.create_user(
        username="requester@example.com",
        email="requester@example.com",
        password="password123",
    )
    approver = User.objects.create_user(
        username="approver@example.com",
        email="approver@example.com",
        password="password123",
    )

    project = Project.objects.create(
        name="Test Project",
        start_date="2024-01-01",
        license_constraints="Test constraints",
        lead=requester,
    )
    box = Box.objects.create(
        number="1",
        location="E",
        box_type="S",
        project=project,
    )
    mouse = Mouse.objects.create(
        project=project,
        sex="M",
        date_of_birth="2024-01-01",
        tube_number=1,
        box=box,
        strain=ensure_strain(),
    )

    request_obj = Request.objects.create(
        creator=requester,
        mouse=mouse,
        project=project,
        kind="B",
        details="Test request",
        status="pending",
    )

    content_type = ContentType.objects.get_for_model(Request)
    approve_perm = Permission.objects.get(
        codename="approve_request", content_type=content_type
    )
    approver.user_permissions.add(approve_perm)

    client.force_login(approver)
    url = reverse("mouseapp:update_request_status", args=[request_obj.pk])
    response = client.post(url, {"status": "accepted"})
    assert response.status_code == 403

    Membership.objects.create(project=project, user=approver)
    response = client.post(url, {"status": "accepted"})
    assert response.status_code == 302
    request_obj.refresh_from_db()
    assert request_obj.status == "accepted"


@pytest.mark.django_db
def test_notification_created_on_status_change(client: Client):
    """Test that notifications are created when request status changes."""
    from .models import Request, Mouse, Project, Box, Notification
    from django.contrib.auth.models import User

    requester = User.objects.create_user(
        username="requester@example.com",
        email="requester@example.com",
        password="password123",
    )
    admin = User.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="password123",
        is_superuser=True,
    )

    project = Project.objects.create(
        name="Test Project",
        start_date="2024-01-01",
        license_constraints="Test constraints",
    )
    box = Box.objects.create(
        number="1",
        location="E",
        box_type="S",
        project=project,
    )
    mouse = Mouse.objects.create(
        project=project,
        sex="M",
        date_of_birth="2024-01-01",
        tube_number=1,
        box=box,
        strain=ensure_strain(),
    )

    request_obj = Request.objects.create(
        creator=requester,
        mouse=mouse,
        project=project,
        kind="B",
        details="Test request",
        status="pending",
    )

    assert Notification.objects.filter(user=requester).count() == 0

    client.force_login(admin)
    url = reverse("mouseapp:update_request_status", args=[request_obj.pk])
    client.post(url, {"status": "accepted"})

    assert Notification.objects.filter(user=requester).count() == 1
    notification = Notification.objects.get(user=requester)
    assert notification.request == request_obj
    assert "accepted" in notification.message.lower()
    assert not notification.read


@pytest.mark.django_db
def test_requests_page_requires_login(client: Client):
    """Test that requests page requires authentication."""
    url = reverse("mouseapp:requests")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url.lower()  # pyright: ignore


@pytest.mark.django_db
def test_notifications_only_visible_to_authenticated_users(client: Client):
    """Test that notifications are handled correctly for authenticated and unauthenticated users."""
    from .models import Notification
    from django.contrib.auth.models import User

    user = User.objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="password123",
    )

    Notification.objects.create(
        user=user,
        message="Test notification",
    )

    response = client.get(reverse("mouseapp:home"))
    assert response.status_code == 200
    assert response.context["unread_count"] == 0

    client.force_login(user)
    response = client.get(reverse("mouseapp:home"))
    assert response.status_code == 200
    assert response.context["unread_count"] == 1
