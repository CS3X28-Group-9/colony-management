from typing import Any, override

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.base_user import BaseUserManager
from django.db.models import Q

from .models import Mouse, Request, Project, RequestReply


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
        model = Mouse
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
        model = Project
        fields = [
            "name",
        ]


class InviteMemberForm(forms.Form):
    user = forms.EmailField()


class RemoveMemberForm(forms.Form):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"] = forms.ChoiceField(
            choices=[(u.id, str(u)) for u in project.researchers.all()]
        )


class RequestForm(forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=True,
        label="Project",
        widget=forms.Select(attrs={"class": "input", "id": "id_project"}),
    )
    mouse = forms.ModelChoiceField(
        queryset=Mouse.objects.none(),
        required=True,
        label="Mouse",
        widget=forms.Select(attrs={"class": "input", "id": "id_mouse"}),
    )
    details = forms.CharField(
        required=True,
        label="Details",
        widget=forms.Textarea(attrs={"class": "input", "rows": 4}),
        help_text="Provide additional details about this request.",
    )

    class Meta:
        model = Request
        fields = ["project", "mouse", "kind", "details"]
        widgets = {
            "kind": forms.HiddenInput(),
        }

    def __init__(self, *args: Any, user: User | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if user:
            accessible_projects = Project.objects.filter(
                Q(lead=user) | Q(researchers=user)
            ).distinct()
            if user.is_superuser:
                accessible_projects = Project.objects.all()

            project_field = self.fields["project"]
            if isinstance(project_field, forms.ModelChoiceField):
                project_field.queryset = accessible_projects

            project = None
            if "project" in self.data:
                try:
                    project_id_str = self.data.get("project")
                    if project_id_str:
                        project_id = int(project_id_str)
                        project = Project.objects.get(id=project_id)
                        if not project.has_read_access(user):
                            project = None
                    else:
                        project = None
                except (ValueError, TypeError, Project.DoesNotExist):
                    project = None
            elif self.instance and self.instance.mouse:
                project = self.instance.mouse.project
                self.fields["project"].initial = project.id
            elif (
                isinstance(project_field, forms.ModelChoiceField)
                and project_field.initial
            ):
                try:
                    project = Project.objects.get(id=project_field.initial)
                    if not project.has_read_access(user):
                        project = None
                except (ValueError, TypeError, Project.DoesNotExist):
                    project = None

            if project:
                self._set_mouse_queryset(project, user)

    def _set_mouse_queryset(self, project: Project, user: User) -> None:
        accessible_mice = [
            mouse
            for mouse in Mouse.objects.filter(project=project)
            if mouse.has_read_access(user)
        ]
        mouse_field = self.fields["mouse"]
        if isinstance(mouse_field, forms.ModelChoiceField):
            mouse_field.queryset = Mouse.objects.filter(
                id__in=[m.id for m in accessible_mice]
            )

    def clean_mouse(self) -> Mouse:
        mouse = self.cleaned_data.get("mouse")
        if not mouse:
            raise ValidationError("A mouse must be selected.")
        project = self.cleaned_data.get("project")
        if project and mouse.project != project:
            raise ValidationError(
                "The selected mouse does not belong to the selected project."
            )
        return mouse


class BreedingRequestForm(RequestForm):
    kind = forms.CharField(
        initial="B",
        widget=forms.HiddenInput(),
    )


class CullingRequestForm(RequestForm):
    kind = forms.CharField(
        initial="C",
        widget=forms.HiddenInput(),
    )


class TransferRequestForm(RequestForm):
    kind = forms.CharField(
        initial="T",
        widget=forms.HiddenInput(),
    )


class RequestReplyForm(forms.ModelForm):
    message = forms.CharField(
        required=True,
        label="Reply",
        widget=forms.Textarea(
            attrs={"class": "input", "rows": 4, "placeholder": "Write your reply..."}
        ),
    )

    class Meta:
        model = RequestReply
        fields = ["message"]
