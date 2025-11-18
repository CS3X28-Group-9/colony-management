from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_safe
from django.conf import settings

from .forms import RegistrationForm, CustomAuthenticationForm, MouseForm, ProjectForm
from .models import Mouse, Project


class AuthedRequest(HttpRequest):
    user: User  # pyright: ignore[reportIncompatibleVariableOverride]


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "mouseapp/home.html")


@require_safe
@login_required
def mouse(request: AuthedRequest, id: int) -> HttpResponse:
    mouse: Mouse = get_object_or_404(Mouse, id=id)
    if not mouse.has_read_access(request.user):
        raise PermissionDenied()
    write_access = mouse.has_write_access(request.user)

    context = {"mouse": mouse, "write_access": write_access}
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
            return HttpResponseRedirect(f"/mouse/{id}")
    else:
        form = MouseForm(instance=mouse)

    return render(request, "mouseapp/edit_mouse.html", {"form": form})


@require_safe
@login_required
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
            return HttpResponseRedirect(f"/project/{id}")
    else:
        form = ProjectForm(instance=project)

    return render(request, "mouseapp/edit_project.html", {"form": form})


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
    def layout_subtree(m: Mouse, start_x: float, level: int):
        children = get_children(m)
        if not children:
            return [
                {
                    "mouse": m,
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
                "mouse": m,
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
    center_mouse = get_object_or_404(Mouse, pk=mouse)
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
