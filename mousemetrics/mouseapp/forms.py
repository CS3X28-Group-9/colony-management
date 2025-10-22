from typing import Any, Dict, cast, override
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import BaseUserManager


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", max_length=254)

    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["placeholder"] = "Enter your email"


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class _Meta:  # This is still a UserCreationForm but with added fields
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    Meta = cast(type[UserCreationForm.Meta], _Meta)

    def clean_email(self) -> str:
        cleaned_data: Dict[str, Any] = self.cleaned_data
        email: str = BaseUserManager.normalize_email(
            cleaned_data["email"]
        )  # normalize so _exact can be used

        if User.objects.filter(
            email__exact=email
        ).exists():  # _exact rather than _iexact to to ensure local normalization
            raise ValidationError("This email is already registered.")
        return email

    @override
    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        if commit:
            user.save()
        return user
