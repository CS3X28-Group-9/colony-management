from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_safe
from django.conf import settings

from .forms import RegistrationForm, CustomAuthenticationForm
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


def get_children(mouse: Mouse) -> list[Mouse]:
    """
    Return a deduplicated list of this mouse's children.
    Merges maternal + paternal children and keeps stable ordering.
    """
    combined = list(mouse.child_set_m.all()) + list(mouse.child_set_f.all())

    seen: set[int] = set()
    ordered: list[Mouse] = []

    for child in combined:
        if child.id not in seen:
            seen.add(child.id)
            ordered.append(child)

    return ordered


def calculate_family_width(mouse: Mouse) -> float:
    """Return the total width needed for this mouse's descendant tree."""
    children = get_children(mouse)

    if not children:
        return 1.0

    return sum(calculate_family_width(child) for child in children)


def layout_family_tree(mouse: Mouse) -> list[dict]:
    """Compute the hierarchical layout (x, y, width) for the descendant tree."""

    def layout_subtree(mouse_obj: Mouse, start_x: float, level: int) -> list[dict]:
        children = get_children(mouse_obj)

        if not children:
            return [
                {
                    "mouse": mouse_obj,
                    "x": start_x + 0.5,
                    "y": level,
                    "width": 1.0,
                }
            ]

        # Layout all children left → right
        current_x = start_x
        nodes: list[dict] = []

        for child in children:
            child_width = calculate_family_width(child)
            nodes.extend(layout_subtree(child, current_x, level + 1))
            current_x += child_width

        # This parent goes centered above all its children
        total_width = current_x - start_x
        nodes.append(
            {
                "mouse": mouse_obj,
                "x": start_x + total_width / 2,
                "y": level,
                "width": total_width,
            }
        )

        return nodes

    return layout_subtree(mouse, 0.0, 0)


def family_tree(request: HttpRequest, mouse: int) -> HttpResponse:
    center_mouse = get_object_or_404(Mouse, pk=mouse)

    # Full ancestry including center
    full_ancestry = family_tree_ancestry(center_mouse)

    # Check if descendants exist
    has_descendants = (
        center_mouse.child_set_m.exists() or center_mouse.child_set_f.exists()
    )

    if has_descendants:
        # Remove last generation so the center mouse isn't duplicated
        ancestry = full_ancestry[:-1]
        tree_layout = layout_family_tree(center_mouse)
    else:
        ancestry = full_ancestry
        tree_layout = []

    return render(
        request,
        "mouseapp/family_tree.html",
        {
            "ancestry": ancestry,
            "tree_layout": tree_layout,
            "center_mouse": center_mouse,
            "has_descendants": has_descendants,
        },
    )
