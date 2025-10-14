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
