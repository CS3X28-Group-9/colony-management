from typing import Any, override

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.base_user import BaseUserManager


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "placeholder": "Enter your email",
                "autocomplete": "email",
                "name": "username",  # ensures Django receives correct field
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
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        ),
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="First name",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Last name",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Last name"}),
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
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user
