from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:  # This is still a UserCreationForm but with added fields
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():  # stops repeat emails
            raise ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):  # creates and saves new user
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email.split("@")[0]
        user.email = email
        if commit:
            user.save()
        return user
