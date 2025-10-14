from django.shortcuts import render, redirect
from .forms import RegistrationForm, CustomAuthenticationForm
from django.contrib.auth import login as auth_login


def home(request):
    return render(request, "mouseapp/home.html")


def login(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("mouseapp:home")
    else:
        form = CustomAuthenticationForm()

    return render(request, "/registration/login.html", {"form": form})


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("mouseapp:login")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})
