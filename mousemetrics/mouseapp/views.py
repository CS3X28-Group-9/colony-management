from django.shortcuts import get_object_or_404, render, redirect
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
from collections import deque, defaultdict
from django.urls import reverse

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
)
from .models import Mouse, Project, Request, Notification
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


def get_children(mouse: Mouse) -> list[Mouse]:
    combined = list(mouse.child_set_m.all()) + list(mouse.child_set_f.all())
    seen: set[int] = set()
    ordered: list[Mouse] = []
    for child in combined:
        if child.id not in seen:
            seen.add(child.id)
            ordered.append(child)
    return ordered


class GraphSVGRenderer:
    BOX_W = 192
    BOX_H = 100
    GAP_X = 40
    GAP_Y = 80

    def __init__(self):
        self.parts = []
        self.min_x = float("inf")
        self.max_x = float("-inf")
        self.min_y = float("inf")
        self.max_y = float("-inf")

    def draw_line(self, x1, y1, x2, y2):
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="2" />'
        )

    def draw_mouse(self, mouse, x, y, is_focus=False):
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x + self.BOX_W)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y + self.BOX_H)

        tree_url = reverse("mouseapp:family_tree", args=[mouse.id])
        detail_url = reverse("mouseapp:mouse", args=[mouse.id])

        strain_text = f"{mouse.strain} {mouse.tube_number}"
        box_text = f"Box: {mouse.box.number if mouse.box else '-'}"
        earmark_text = f"Earmark: {mouse.earmark if mouse.earmark else '-'}"

        mouse_svg = f"""
        <g id="mouse-{mouse.id}">
            <rect x="{x}" y="{y}" width="{self.BOX_W}" height="{self.BOX_H}"
                  fill="white" stroke="#e5e7eb" stroke-width="1" rx="6" />

            <a href="{tree_url}">
                <text x="{x + 8}" y="{y + 20}"
                      font-family="sans-serif" font-size="14" fill="#2563eb">
                    {strain_text}
                </text>
            </a>

            <text x="{x + 8}" y="{y + 45}"
                  font-family="sans-serif" font-size="14" fill="black">
                {box_text}
            </text>

            <text x="{x + 8}" y="{y + 65}"
                  font-family="sans-serif" font-size="14" fill="black">
                {earmark_text}
            </text>

            <a href="{detail_url}">
                <text x="{x + 184}" y="{y + 90}" text-anchor="end"
                      font-family="sans-serif" font-size="10" fill="#2563eb">
                    (Details)
                </text>
            </a>
        </g>
        """
        self.parts.append(mouse_svg)

    def get_final_svg(self):
        if not self.parts:
            return "<svg></svg>"

        padding = 50
        width = (self.max_x - self.min_x) + (padding * 2)
        height = (self.max_y - self.min_y) + (padding * 2)

        viewbox = f"{self.min_x - padding} {self.min_y - padding} {width} {height}"

        header = f'<svg width="{width}" height="{height}" viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg">'
        footer = "</svg>"
        return header + "".join(self.parts) + footer


def get_descendant_graph(start_mouse, max_depth=10):
    all_nodes = {start_mouse}
    queue = deque([(start_mouse, 0)])

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue

        relatives = []
        if current.father:
            relatives.append(current.father)
        if current.mother:
            relatives.append(current.mother)

        children = list(Mouse.objects.filter(father=current)) + list(
            Mouse.objects.filter(mother=current)
        )
        relatives.extend(children)

        for r in relatives:
            if r not in all_nodes:
                all_nodes.add(r)
                queue.append((r, depth + 1))

    adj = defaultdict(list)
    in_degree = {m: 0 for m in all_nodes}

    for m in all_nodes:
        if m.father and m.father in all_nodes:
            adj[m.father].append(m)
            in_degree[m] += 1

        if m.mother and m.mother in all_nodes:
            adj[m.mother].append(m)
            in_degree[m] += 1

    queue = deque([m for m, deg in in_degree.items() if deg == 0])
    ranks = {}

    while queue:
        node = queue.popleft()

        parent_ranks = []
        if node.father and node.father in ranks:
            parent_ranks.append(ranks[node.father])
        if node.mother and node.mother in ranks:
            parent_ranks.append(ranks[node.mother])

        if not parent_ranks:
            ranks[node] = 0
        else:
            ranks[node] = max(parent_ranks) + 1

        for child in adj[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    for m in all_nodes:
        if m not in ranks:
            ranks[m] = 0

    layers = defaultdict(list)
    for m, rank in ranks.items():
        layers[rank].append(m)

    return layers


def layout_graph(renderer, start_mouse):
    layers = get_descendant_graph(start_mouse)
    positions = {}  # Store positions of each mouse box for line drawing

    sorted_ranks = sorted(layers.keys())
    current_y = 0

    for rank in sorted_ranks:  # draw layer by layer
        mice_in_layer = layers[rank]
        mice_in_layer.sort(
            key=lambda m: (
                m.father_id if m.father else 0,
                m.mother_id if m.mother else 0,
            )
        )

        row_width = (
            len(mice_in_layer) * renderer.BOX_W
            + (len(mice_in_layer) - 1) * renderer.GAP_X
        )
        start_x = -(row_width / 2)

        for m in mice_in_layer:
            renderer.draw_mouse(
                m, start_x, current_y, is_focus=(m.id == start_mouse.id)
            )

            center_x = start_x + (renderer.BOX_W / 2)
            positions[m.id] = {
                "top_x": center_x,
                "top_y": current_y,
                "bottom_x": center_x,
                "bottom_y": current_y + renderer.BOX_H,
            }

            start_x += renderer.BOX_W + renderer.GAP_X

        current_y += renderer.BOX_H + renderer.GAP_Y

    all_drawn_mice = [
        m for sublist in layers.values() for m in sublist
    ]  # draw lines after all boxes are drawn

    for m in all_drawn_mice:
        child_pos = positions[m.id]

        if m.father and m.father.id in positions:
            father_pos = positions[m.father.id]
            renderer.draw_line(
                father_pos["bottom_x"],
                father_pos["bottom_y"],
                child_pos["top_x"],
                child_pos["top_y"],
            )

        if m.mother and m.mother.id in positions:
            mother_pos = positions[m.mother.id]
            renderer.draw_line(
                mother_pos["bottom_x"],
                mother_pos["bottom_y"],
                child_pos["top_x"],
                child_pos["top_y"],
            )


def family_tree(request: HttpRequest, mouse: int) -> HttpResponse:
    center_mouse = get_object_or_404(Mouse, id=mouse)
    renderer = GraphSVGRenderer()

    layout_graph(renderer, center_mouse)  # layout and draw the graph

    return render(
        request,
        "mouseapp/family_tree.html",
        {
            "svg_content": renderer.get_final_svg(),
            "center_mouse": center_mouse,
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
