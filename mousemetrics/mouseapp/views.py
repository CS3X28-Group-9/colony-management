from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_safe, require_http_methods
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import date

from .forms import (
    RegistrationForm,
    CustomAuthenticationForm,
    BreedingRequestForm,
    CullingRequestForm,
    TransferRequestForm,
)
from .models import Mouse, Project, Request, Notification
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class AuthedRequest(HttpRequest):
    user: User  # pyright: ignore[reportIncompatibleVariableOverride]


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "mouseapp/home.html")


def get_users_to_notify_for_request(request_obj: Request) -> list[User]:
    """Get all users who should be notified when a request is created."""
    users_to_notify = []

    users_to_notify.extend(User.objects.filter(is_superuser=True))

    if request_obj.project and request_obj.project.lead:
        if request_obj.project.lead not in users_to_notify:
            users_to_notify.append(request_obj.project.lead)

    try:
        content_type = ContentType.objects.get_for_model(Request)
        approve_perm = Permission.objects.get(
            codename="approve_request", content_type=content_type
        )
        users_with_perm = User.objects.filter(
            Q(user_permissions=approve_perm) | Q(groups__permissions=approve_perm)
        ).distinct()
        for user in users_with_perm:
            if user not in users_to_notify:
                users_to_notify.append(user)
    except Permission.DoesNotExist:
        pass

    return [user for user in users_to_notify if user != request_obj.creator]


@require_safe
@login_required
def mouse(request: AuthedRequest, id: int) -> HttpResponse:
    mouse: Mouse = get_object_or_404(Mouse, id=id)
    if not mouse.has_read_access(request.user):
        raise PermissionDenied()
    write_access = mouse.has_write_access(request.user)

    mouse_requests = Request.objects.filter(mouse=mouse).order_by("-created_at")

    requests_with_permissions = []
    for req in mouse_requests:
        req.can_change_status = req.can_change_status(
            request.user
        )  # pyright: ignore[reportAttributeAccessIssue]
        requests_with_permissions.append(req)

    context = {
        "mouse": mouse,
        "write_access": write_access,
        "mouse_requests": requests_with_permissions,
    }
    return render(request, "mouseapp/mouse.html", context)


@require_safe
@login_required
def project(request: AuthedRequest, id: int) -> HttpResponse:
    project = get_object_or_404(Project, id=id)
    if not project.has_read_access(request.user):
        raise PermissionDenied()
    write_access = project.has_write_access(request.user)

    context = {"project": project, "write_access": write_access}
    return render(request, "mouseapp/project.html", context)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            remember_me = form.cleaned_data.get("remember_me")
            if not remember_me:
                request.session.set_expiry(0)
                auth_login(request, form.get_user())
            return redirect("mouseapp:home")
    else:
        form = CustomAuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


def register(request: HttpRequest) -> HttpResponse:
    if not settings.ENABLE_REGISTRATION:
        raise PermissionDenied()
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("mouseapp:login")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def family_tree_ancestry(mouse: Mouse) -> list[list[Mouse | None]]:
    """Lay out the ancestry half of the family tree
    Return effectively the generations of mice: each generation is an entry in the list
    Includes `None` where no such mouse exists, so that the tree is complete

    See tests in `family_tree_test.py` for examples
    """

    def parents(mouse: Mouse | None) -> list[Mouse | None]:
        if mouse is not None:
            return [mouse.father, mouse.mother]
        return [None, None]

    ancestry: list[list[Mouse | None]] = [[mouse]]
    while any(any(parents(mouse)) for mouse in ancestry[-1]):
        ancestry.append([])
        for parent in ancestry[-2]:
            ancestry[-1].extend(parents(parent))
    ancestry.reverse()

    return ancestry


def family_tree(request, mouse):
    mouse = get_object_or_404(Mouse, pk=mouse)
    ancestry = family_tree_ancestry(mouse)

    return render(request, "mouseapp/family_tree.html", {"ancestry": ancestry})


@login_required
@require_http_methods(["GET", "POST"])
def create_breeding_request(request: AuthedRequest) -> HttpResponse:
    mouse_id = None
    if request.method == "POST":
        form = BreedingRequestForm(request.POST, user=request.user)
        if form.is_valid():
            request_obj = form.save(commit=False)
            request_obj.creator = request.user
            request_obj.kind = "B"
            if request_obj.mouse:
                request_obj.project = request_obj.mouse.project
            request_obj.save()

            users_to_notify = get_users_to_notify_for_request(request_obj)
            for user in users_to_notify:
                Notification.objects.create(
                    user=user,
                    request=request_obj,
                    message="New request created. [link]",
                )

            messages.success(request, "Breeding request created successfully.")
            return redirect("mouseapp:requests")
    else:
        form = BreedingRequestForm(user=request.user)
        mouse_id = request.GET.get("mouse")
        if mouse_id:
            try:
                mouse = Mouse.objects.get(id=mouse_id)
                if mouse.has_read_access(request.user):
                    form.fields["mouse"].initial = mouse.pk
            except Mouse.DoesNotExist:
                pass

    context = {
        "form": form,
        "request_type": "Breeding",
        "request_type_code": "B",
    }
    if mouse_id:
        context["mouse_id"] = mouse_id
    return render(request, "mouseapp/create_request.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def create_culling_request(request: AuthedRequest) -> HttpResponse:
    mouse_id = None
    if request.method == "POST":
        form = CullingRequestForm(request.POST, user=request.user)
        if form.is_valid():
            request_obj = form.save(commit=False)
            request_obj.creator = request.user
            request_obj.kind = "C"
            if request_obj.mouse:
                request_obj.project = request_obj.mouse.project
            request_obj.save()

            users_to_notify = get_users_to_notify_for_request(request_obj)
            for user in users_to_notify:
                Notification.objects.create(
                    user=user,
                    request=request_obj,
                    message="New request created. [link]",
                )

            messages.success(request, "Culling request created successfully.")
            return redirect("mouseapp:requests")
    else:
        form = CullingRequestForm(user=request.user)
        mouse_id = request.GET.get("mouse")
        if mouse_id:
            try:
                mouse = Mouse.objects.get(id=mouse_id)
                if mouse.has_read_access(request.user):
                    form.fields["mouse"].initial = mouse.pk
            except Mouse.DoesNotExist:
                pass

    context = {
        "form": form,
        "request_type": "Culling",
        "request_type_code": "C",
    }
    if mouse_id:
        context["mouse_id"] = mouse_id
    return render(request, "mouseapp/create_request.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def create_transfer_request(request: AuthedRequest) -> HttpResponse:
    mouse_id = None
    if request.method == "POST":
        form = TransferRequestForm(request.POST, user=request.user)
        if form.is_valid():
            request_obj = form.save(commit=False)
            request_obj.creator = request.user
            request_obj.kind = "T"
            if request_obj.mouse:
                request_obj.project = request_obj.mouse.project
            request_obj.save()

            users_to_notify = get_users_to_notify_for_request(request_obj)
            for user in users_to_notify:
                Notification.objects.create(
                    user=user,
                    request=request_obj,
                    message="New request created. [link]",
                )

            messages.success(request, "Transfer request created successfully.")
            return redirect("mouseapp:requests")
    else:
        form = TransferRequestForm(user=request.user)
        mouse_id = request.GET.get("mouse")
        if mouse_id:
            try:
                mouse = Mouse.objects.get(id=mouse_id)
                if mouse.has_read_access(request.user):
                    form.fields["mouse"].initial = mouse.pk
            except Mouse.DoesNotExist:
                pass

    context = {
        "form": form,
        "request_type": "Transfer",
        "request_type_code": "T",
    }
    if mouse_id:
        context["mouse_id"] = mouse_id
    return render(request, "mouseapp/create_request.html", context)


@login_required
@require_safe
def requests_list(request: AuthedRequest) -> HttpResponse:
    user_requests = Request.objects.none()

    if request.user.is_superuser or request.user.has_perm("mouseapp.approve_request"):
        user_requests = Request.objects.all()
    else:
        user_requests = Request.objects.filter(creator=request.user)
        user_projects = Project.objects.filter(
            Q(lead=request.user) | Q(researchers=request.user)
        ).distinct()
        project_requests = Request.objects.filter(project__in=user_projects)
        user_requests = (user_requests | project_requests).distinct()

    status_filter = request.GET.get("status", "")
    if status_filter in ["pending", "accepted", "denied", "completed"]:
        user_requests = user_requests.filter(status=status_filter)

    type_filter = request.GET.get("type", "")
    if type_filter in ["B", "C", "T", "Q"]:
        user_requests = user_requests.filter(kind=type_filter)

    requests_with_permissions = []
    for req in user_requests:
        req.can_change_status = req.can_change_status(
            request.user
        )  # pyright: ignore[reportAttributeAccessIssue]
        requests_with_permissions.append(req)

    request_id = request.GET.get("id")
    highlighted_request_id = None
    page_number = request.GET.get("page")

    paginator = Paginator(requests_with_permissions, 10)

    if request_id:
        try:
            highlighted_request_id = int(request_id)
            for idx, req in enumerate(requests_with_permissions):
                if req.id == highlighted_request_id:
                    page_number = (idx // 10) + 1
                    break
        except (ValueError, TypeError):
            pass

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "requests": page_obj,
        "status_filter": status_filter,
        "type_filter": type_filter,
        "highlighted_request_id": highlighted_request_id,
    }
    return render(request, "mouseapp/requests.html", context)


@login_required
@require_http_methods(["POST"])
def update_request_status(request: AuthedRequest, request_id: int) -> HttpResponse:
    request_obj = get_object_or_404(Request, id=request_id)

    if not request_obj.can_change_status(request.user):
        raise PermissionDenied(
            "You do not have permission to change this request's status."
        )

    new_status = request.POST.get("status")
    if new_status not in ["pending", "accepted", "denied", "completed"]:
        messages.error(request, "Invalid status.")
        return redirect("mouseapp:requests")

    old_status = request_obj.status
    request_obj.status = new_status

    if new_status == "accepted" and not request_obj.approved_date:
        request_obj.approved_date = date.today()
        request_obj.approver = request.user
    if new_status == "completed" and not request_obj.fulfill_date:
        request_obj.fulfill_date = date.today()

    request_obj.save()

    if (
        old_status != new_status
        and new_status in ["accepted", "denied", "completed"]
        and request_obj.creator != request.user
    ):
        status_display = dict(Request.STATUS_CHOICES).get(new_status, new_status)
        message = f"Request {status_display.lower()}. [link]"
        Notification.objects.create(
            user=request_obj.creator,
            request=request_obj,
            message=message,
        )

    messages.success(request, f"Request status updated to {new_status}.")
    return redirect("mouseapp:requests")


@login_required
@require_http_methods(["POST"])
def mark_notification_read(
    request: AuthedRequest, notification_id: int
) -> HttpResponse:
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.delete()
    return redirect("mouseapp:home")


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request: AuthedRequest) -> HttpResponse:
    Notification.objects.filter(user=request.user, read=False).delete()
    messages.success(request, "All notifications marked as read.")
    return redirect("mouseapp:home")
