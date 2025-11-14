from typing import Any, override

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.base_user import BaseUserManager

from . import models


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "name": "username",  # ensures Django receives correct field
            }
        ),
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "bg-gray-50 border border-gray-300 focus:ring-3 focus:ring-blue-300 h-4 w-4 rounded",
            }
        ),
    )

    @override
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Style password field
        self.fields["password"].widget.attrs.update(
            {"class": "input", "autocomplete": "current-password"}
        )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
            }
        ),
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "input"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    @override
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "input", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "input", "autocomplete": "new-password"}
        )

    def clean_email(self) -> str:
        cleaned_data = self.cleaned_data
        email = BaseUserManager.normalize_email(cleaned_data["email"])
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    @override
    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        user.first_name = self.cleaned_data["first_name"].capitalize()
        user.last_name = self.cleaned_data["last_name"].capitalize()
        if commit:
            user.save()
        return user


class MouseForm(forms.ModelForm):
    class Meta:
        model = models.Mouse
        fields = [
            "coat_colour",
            "sex",
            "mother",
            "father",
            "date_of_birth",
            "tube_number",
            "cull_date",
            "cull_reason",
            "box",
            "strain",
            "coat_colour",
            "earmark",
            "notes",
        ]
        widgets = {
            "coat_colour": forms.TextInput,
            "cull_reason": forms.TextInput,
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = models.Project
        fields = [
            "name",
        ]
