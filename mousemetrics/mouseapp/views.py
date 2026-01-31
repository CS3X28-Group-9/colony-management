from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.mail import send_mail
from django.core import signing
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import date

from .forms import (
    RegistrationForm,
    CustomAuthenticationForm,
    InviteMemberForm,
    MouseForm,
    ProjectForm,
    RemoveMemberForm,
    BreedingRequestForm,
    CullingRequestForm,
    TransferRequestForm,
    RequestReplyForm,
)
from .models import Mouse, Project, Request, Notification, RequestReply, ReplyReaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class AuthedRequest(HttpRequest):
    user: User  # pyrefly: ignore[bad-override]


def home(request: HttpRequest) -> HttpResponse:
    context: dict[str, object] = {}
    if request.user.is_authenticated:
        context["notifications"] = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")[:10]
        context["unread_count"] = Notification.objects.filter(
            user=request.user, read=False
        ).count()
    return render(request, "mouseapp/home.html", context)


def privacy_policy(request: HttpRequest) -> HttpResponse:
    context: dict[str, object] = {}
    if request.user.is_authenticated:
        context["notifications"] = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")[:10]
        context["unread_count"] = Notification.objects.filter(
            user=request.user, read=False
        ).count()
    return render(request, "mouseapp/privacy_policy.html", context)


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


@login_required
@require_http_methods(["GET", "POST"])
def mouse(request: AuthedRequest, id: int) -> HttpResponse:
    mouse: Mouse = get_object_or_404(Mouse, id=id)
    if not mouse.has_read_access(request.user):
        raise PermissionDenied()
    write_access = mouse.has_write_access(request.user)

    mouse_requests = Request.objects.filter(mouse=mouse).order_by("-created_at")

    requests_with_permissions = []
    for req in mouse_requests:
        req._user = request.user
        requests_with_permissions.append(req)

    context = {
        "mouse": mouse,
        "write_access": write_access,
        "mouse_requests": requests_with_permissions,
    }
    return render(request, "mouseapp/mouse.html", context)


@login_required
def edit_mouse(request: AuthedRequest, id: int) -> HttpResponse:
    mouse: Mouse = get_object_or_404(Mouse, id=id)
    if not mouse.has_write_access(request.user):
        raise PermissionDenied()

    if request.method == "POST":
        form = MouseForm(request.POST, instance=mouse)
        if form.is_valid():
            form.save()
            return redirect(mouse)
    else:
        form = MouseForm(instance=mouse)

    return render(request, "mouseapp/edit_mouse.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def project(request: AuthedRequest, id: int) -> HttpResponse:
    project = get_object_or_404(Project, id=id)
    if not project.has_read_access(request.user):
        raise PermissionDenied()
    write_access = project.has_write_access(request.user)

    context = {"project": project, "write_access": write_access}
    return render(request, "mouseapp/project.html", context)


@login_required
def edit_project(request: AuthedRequest, id: int) -> HttpResponse:
    project: Project = get_object_or_404(Project, id=id)
    if not project.has_write_access(request.user):
        raise PermissionDenied()

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect(project)
    else:
        form = ProjectForm(instance=project)

    return render(request, "mouseapp/edit_project.html", {"form": form})


@login_required
def invite_member(request: AuthedRequest, id: int) -> HttpResponse:
    project: Project = get_object_or_404(Project, id=id)
    if not project.has_write_access(request.user):
        raise PermissionDenied()

    if request.method == "POST":
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["user"]
            try:
                user = User.objects.get(email=email)
                token = signing.dumps(
                    {
                        "user": user.pk,
                        "project": project.id,
                    }
                )
                mail_html = render_to_string(
                    "mouseapp/invite_email.html",
                    context={
                        "token": token,
                        "protocol": request.scheme,
                        "domain": request.get_host(),
                        "project": project,
                    },
                )
                mail_text = strip_tags(mail_html)
                send_mail(
                    subject=f"Invitation to {project.name}",
                    message=mail_text,
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                    html_message=mail_html,
                )
            except ObjectDoesNotExist:
                pass

            return redirect(project)
    else:
        form = InviteMemberForm()

    return render(request, "mouseapp/invite_member.html", {"form": form})


@login_required
def remove_member(request: AuthedRequest, id: int) -> HttpResponse:
    project: Project = get_object_or_404(Project, id=id)
    if not project.has_write_access(request.user):
        raise PermissionDenied()

    if request.method == "POST":
        form = RemoveMemberForm(project, request.POST)
        if form.is_valid():
            user = User.objects.get(id=form.cleaned_data["user"])
            project.researchers.remove(user)
            return redirect(project)
    else:
        form = RemoveMemberForm(project)

    return render(request, "mouseapp/remove_member.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def join_project(request: AuthedRequest, token: str) -> HttpResponse:
    SECONDS_IN_MONTH = 60 * 60 * 24 * 31

    data = signing.loads(token, max_age=SECONDS_IN_MONTH)
    try:
        user_id = data["user"]
        project_id = data["project"]
    except KeyError as e:
        raise PermissionDenied from e

    if user_id != request.user.pk:
        raise PermissionDenied

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist as e:
        raise PermissionDenied from e

    project.researchers.add(request.user)
    return redirect(project)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            remember_me = form.cleaned_data.get("remember_me")
            if not remember_me:
                request.session.set_expiry(0)  # Session expires on browser close
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
    def parents(m: Mouse | None) -> list[Mouse | None]:
        if m is not None:
            return [m.father, m.mother]
        return [None, None]

    ancestry: list[list[Mouse | None]] = [[mouse]]
    while any(any(parents(m)) for m in ancestry[-1]):
        ancestry.append([])
        for parent in ancestry[-2]:
            ancestry[-1].extend(parents(parent))
    ancestry.reverse()
    return ancestry


def get_children(mouse: Mouse) -> list[Mouse]:
    combined = list(mouse.child_set_m.all()) + list(mouse.child_set_f.all())
    seen: set[int] = set()
    ordered: list[Mouse] = []
    for child in combined:
        if child.id not in seen:
            seen.add(child.id)
            ordered.append(child)
    return ordered


def get_descendant_depth(mouse: Mouse) -> int:
    children = get_children(mouse)
    if not children:
        return 0
    return 1 + max(get_descendant_depth(child) for child in children)


def layout_family_tree_with_depth(mouse: Mouse) -> list[dict]:
    def layout_subtree(mouse: Mouse, start_x: float, level: int):
        children = get_children(mouse)
        if not children:
            return [
                {
                    "mouse": mouse,
                    "x": start_x + 0.5,
                    "y": level,
                    "depth": 0,
                }
            ], 1.0

        current_x = start_x
        nodes = []
        max_child_depth = 0
        for child in children:
            subtree_nodes, width = layout_subtree(child, current_x, level + 1)
            nodes.extend(subtree_nodes)
            current_x += width
            max_child_depth = max(max_child_depth, subtree_nodes[-1]["depth"])

        total_width = current_x - start_x
        nodes.append(
            {
                "mouse": mouse,
                "x": start_x + total_width / 2,
                "y": level,
                "depth": 1 + max_child_depth,
            }
        )
        return nodes, total_width

    tree_nodes, _ = layout_subtree(mouse, 0.0, 0)
    return tree_nodes


def gridify_descendants(tree_layout: list[dict]) -> list[list[dict | None]]:
    from collections import defaultdict

    levels = defaultdict(list)
    for node in tree_layout:
        levels[node["y"]].append(node)

    grid = []
    for y in sorted(levels.keys()):
        row_nodes = sorted(levels[y], key=lambda n: n["x"])
        col_map = {int(n["x"] - 0.5): n for n in row_nodes}
        min_col = min(col_map.keys())
        max_col = max(col_map.keys())
        row = [col_map.get(col) for col in range(min_col, max_col + 1)]
        grid.append(row)
    return grid


def family_tree(request: HttpRequest, mouse: int) -> HttpResponse:
    center_mouse = get_object_or_404(Mouse, id=mouse)
    full_ancestry = family_tree_ancestry(center_mouse)

    has_descendants = (
        center_mouse.child_set_m.exists() or center_mouse.child_set_f.exists()
    )

    if has_descendants:
        ancestry = full_ancestry[:-1]
        layout = layout_family_tree_with_depth(center_mouse)
        descendants_grid = gridify_descendants(layout)
    else:
        ancestry = full_ancestry
        descendants_grid = []
    return render(
        request,
        "mouseapp/family_tree.html",
        {
            "ancestry": ancestry,
            "descendants_grid": descendants_grid,
            "center_mouse": center_mouse,
            "has_descendants": has_descendants,
        },
    )


def _prepare_request_form(
    request: AuthedRequest, form_class, request_type: str, request_code: str
) -> tuple:
    mouse_id = None
    mouse = None
    project_id = None
    project = None

    if request.method == "POST":
        form = form_class(request.POST, user=request.user)
        if form.is_valid():
            request_obj = form.save(commit=False)
            request_obj.creator = request.user
            request_obj.kind = request_code
            if request_obj.mouse and request_obj.project != request_obj.mouse.project:
                request_obj.project = request_obj.mouse.project
            request_obj.save()

            users_to_notify = get_users_to_notify_for_request(request_obj)
            for user in users_to_notify:
                Notification.objects.create(
                    user=user,
                    request=request_obj,
                    message=f"New {request_type.lower()} request created.",
                )

            return (
                redirect("mouseapp:requests"),
                form,
                mouse_id,
                None,
                None,
            )
    else:
        mouse_id = request.GET.get("mouse")
        project_id = request.GET.get("project")
        project = None
        initial = {}

        if mouse_id:
            try:
                mouse_id_int = int(mouse_id)
                mouse = Mouse.objects.get(id=mouse_id_int)
                if mouse.has_read_access(request.user):
                    initial["mouse"] = mouse.id
                    initial["project"] = mouse.project.id
                    project_id = mouse.project.id
                    project = mouse.project
                else:
                    mouse_id = None
                    mouse = None
            except (ValueError, TypeError, Mouse.DoesNotExist):
                mouse_id = None
                mouse = None

        if project_id and not mouse_id:
            try:
                project_id_int = int(project_id)
                project = Project.objects.get(id=project_id_int)
                if project.has_read_access(request.user):
                    initial["project"] = project.id
                else:
                    project_id = None
                    project = None
            except (ValueError, TypeError, Project.DoesNotExist):
                project_id = None
                project = None

        form = form_class(user=request.user, initial=initial or {})
        if project:
            form._set_mouse_queryset(project, request.user)

    return (
        None,
        form,
        mouse_id,
        project,
        mouse,
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_breeding_request(request: AuthedRequest) -> HttpResponse:
    redirect_response, form, mouse_id, project, mouse = _prepare_request_form(
        request, BreedingRequestForm, "Breeding", "B"
    )
    if redirect_response:
        return redirect_response
    return render(
        request,
        "mouseapp/create_request.html",
        {
            "form": form,
            "request_type": "Breeding",
            "request_type_code": "B",
            "mouse_id": mouse_id,
            "project": project,
            "mouse": mouse,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_culling_request(request: AuthedRequest) -> HttpResponse:
    redirect_response, form, mouse_id, project, mouse = _prepare_request_form(
        request, CullingRequestForm, "Culling", "C"
    )
    if redirect_response:
        return redirect_response
    return render(
        request,
        "mouseapp/create_request.html",
        {
            "form": form,
            "request_type": "Culling",
            "request_type_code": "C",
            "mouse_id": mouse_id,
            "project": project,
            "mouse": mouse,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_transfer_request(request: AuthedRequest) -> HttpResponse:
    redirect_response, form, mouse_id, project, mouse = _prepare_request_form(
        request, TransferRequestForm, "Transfer", "T"
    )
    if redirect_response:
        return redirect_response
    return render(
        request,
        "mouseapp/create_request.html",
        {
            "form": form,
            "request_type": "Transfer",
            "request_type_code": "T",
            "mouse_id": mouse_id,
            "project": project,
            "mouse": mouse,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def requests_list(request: AuthedRequest) -> HttpResponse:
    if request.user.is_superuser or request.user.has_perm("mouseapp.approve_request"):
        user_requests = Request.objects.all()
    else:
        user_projects = Project.objects.filter(
            Q(lead=request.user) | Q(researchers=request.user)
        ).distinct()
        if not user_projects.exists():
            raise PermissionDenied(
                "You must be a member of at least one project to access requests."
            )
        user_requests = Request.objects.filter(creator=request.user)
        project_requests = Request.objects.filter(project__in=user_projects)
        user_requests = (user_requests | project_requests).distinct()

    status_filter = request.GET.get("status", "")
    if status_filter in Request.STATUS_CHOICES:
        user_requests = user_requests.filter(status=status_filter)

    type_filter = request.GET.get("type", "")
    if type_filter in Request.REQUEST_CHOICES:
        user_requests = user_requests.filter(kind=type_filter)

    requests_with_permissions = []
    for req in user_requests.order_by("-created_at"):
        req._user = request.user
        requests_with_permissions.append(req)

    request_id = request.GET.get("id", None)
    highlighted_request_id = None
    page_number = request.GET.get("page", 1)

    paginator = Paginator(requests_with_permissions, 10)

    if request_id is not None:
        try:
            highlighted_request_id = int(request_id)
            for index, req in enumerate(requests_with_permissions):
                if req.id == highlighted_request_id:
                    page_number = (index // paginator.per_page) + 1
                    break
        except (ValueError, TypeError):
            highlighted_request_id = None

    page_obj = paginator.get_page(page_number)

    all_accessible_request_ids = [req.id for req in requests_with_permissions]
    if all_accessible_request_ids:
        Notification.objects.filter(
            user=request.user, request_id__in=all_accessible_request_ids
        ).delete()

    if highlighted_request_id:
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        query_params = []
        if status_filter:
            query_params.append(f"status={status_filter}")
        if type_filter:
            query_params.append(f"type={type_filter}")
        if page_obj.number != 1:
            query_params.append(f"page={page_obj.number}")
        query_string = "&".join(query_params)
        url = reverse("mouseapp:requests")
        if query_string:
            url = f"{url}?{query_string}"
        url = f"{url}#request-{highlighted_request_id}"
        return HttpResponseRedirect(url)

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "type_filter": type_filter,
        "highlighted_request_id": highlighted_request_id,
    }
    return render(request, "mouseapp/requests.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def request_detail(request: AuthedRequest, request_id: int) -> HttpResponse:
    request_obj = get_object_or_404(Request, id=request_id)

    # Check read access
    if not request_obj.has_read_access(request.user):
        raise PermissionDenied("You do not have access to this request.")

    # Handle reply submission
    quoted_reply_id = request.GET.get("quote")
    quoted_reply = None
    reply_form = RequestReplyForm()
    if quoted_reply_id:
        try:
            quoted_reply = RequestReply.objects.get(
                id=quoted_reply_id, request=request_obj
            )
            reply_form = RequestReplyForm(initial={"quoted_reply_id": quoted_reply_id})
        except RequestReply.DoesNotExist:
            pass

    if request.method == "POST":
        reply_form = RequestReplyForm(request.POST)
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.request = request_obj
            reply.user = request.user
            # Handle quoted_reply_id from form
            quoted_reply_id = reply_form.cleaned_data.get("quoted_reply_id")
            if quoted_reply_id:
                try:
                    quoted_reply = RequestReply.objects.get(
                        id=quoted_reply_id, request=request_obj
                    )
                    reply.quoted_reply = quoted_reply
                except RequestReply.DoesNotExist:
                    pass
            reply.save()
            return redirect(reverse("mouseapp:request_detail", args=[request_id]))

    # Get paginated replies (newest first for pagination)
    replies = request_obj.replies.all().order_by("-timestamp")  # type: ignore[attr-defined]
    paginator = Paginator(replies, 4)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    # Reverse items for display (oldest at bottom, newest at top)
    page_obj.object_list = list(reversed(page_obj.object_list))

    user_can_change_status = request_obj.can_change_status(request.user)

    reply_ids = [reply.id for reply in page_obj.object_list]
    reactions = ReplyReaction.objects.filter(reply__id__in=reply_ids).select_related(
        "user", "reply"
    )
    reactions_by_reply = {}
    user_reactions_by_reply = {}  # Track which emojis the current user has reacted with

    for reaction in reactions:
        reactions_by_reply.setdefault(reaction.reply.id, {}).setdefault(
            reaction.emoji, []
        ).append(reaction.user)

        # Track user's reactions
        if reaction.user == request.user:
            user_reactions_by_reply.setdefault(reaction.reply.id, set()).add(
                reaction.emoji
            )

    context = {
        "request_obj": request_obj,
        "reply_form": reply_form,
        "page_obj": page_obj,
        "user_can_change_status": user_can_change_status,
        "reactions_by_reply": reactions_by_reply,
        "user_reactions_by_reply": user_reactions_by_reply,
        "quoted_reply": quoted_reply,
    }
    return render(request, "mouseapp/request_detail.html", context)


@login_required
@require_http_methods(["POST"])
def update_request_status(request: AuthedRequest, request_id: int) -> HttpResponse:
    request_obj = get_object_or_404(Request, id=request_id)

    if not request_obj.can_change_status(request.user):
        raise PermissionDenied(
            "You do not have permission to change this request's status."
        )

    new_status = request.POST.get("status")
    if new_status not in Request.STATUS_CHOICES:
        return redirect("mouseapp:requests")

    old_status = request_obj.status
    request_obj.status = new_status

    if new_status == "A" and not request_obj.approved_date:
        request_obj.approved_date = date.today()
        request_obj.approver = request.user
    if new_status == "C" and not request_obj.fulfill_date:
        request_obj.fulfill_date = date.today()

    request_obj.save()

    if (
        old_status != new_status
        and new_status in ["A", "D", "C"]
        and request_obj.creator != request.user
    ):
        status_display = Request.STATUS_CHOICES[new_status]
        message = f"Request {status_display.lower()}. [link]"
        Notification.objects.create(
            user=request_obj.creator,
            request=request_obj,
            message=message,
        )

    return redirect("mouseapp:requests")


@login_required
@require_http_methods(["POST"])
def toggle_reply_reaction(request: AuthedRequest, reply_id: int) -> HttpResponse:
    reply = get_object_or_404(RequestReply, id=reply_id)

    # Check access to the request
    request_obj = reply.request
    if not request_obj.has_read_access(request.user):
        raise PermissionDenied("You do not have access to this request.")

    emoji = request.POST.get("emoji", "").strip()

    # Toggle reaction (add if doesn't exist, remove if exists)
    reaction, created = ReplyReaction.objects.get_or_create(
        reply=reply,
        user=request.user,
        emoji=emoji,
    )

    if not created:
        # Reaction already exists, remove it
        reaction.delete()

    return redirect(
        reverse("mouseapp:request_detail", args=[request_obj.id]) + "#reply-form"
    )


@login_required
@require_http_methods(["POST"])
def mark_notification_read(
    request: AuthedRequest, notification_id: int
) -> HttpResponse:
    try:
        Notification.objects.get(id=notification_id, user=request.user).delete()
    except Notification.DoesNotExist:
        pass
    return redirect("mouseapp:home")


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request: AuthedRequest) -> HttpResponse:
    Notification.objects.filter(user=request.user).delete()
    return redirect("mouseapp:home")
