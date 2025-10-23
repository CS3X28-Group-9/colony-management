from typing import Any
from django.db import models
from django.db.models import SET_NULL
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


class Project(models.Model):
    lead: models.ForeignKey[Any, Any] = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=SET_NULL,
        related_name="leading_set",
    )
    researchers: "models.ManyToManyField[Any, Any]" = models.ManyToManyField(
        User, through="Membership", through_fields=("project", "user")
    )
    license_constraints: "models.TextField[Any, Any]" = models.TextField()

    class Meta:
        permissions = [("create_project", "Create projects")]

    def has_read_access(self, user: User) -> bool:
        try:
            if user == self.lead:
                return True
        except ObjectDoesNotExist:
            pass

        return bool(user.is_superuser or self.researchers.filter(id=user.pk).exists())  # type: ignore reportUnknownMemberType, reportUnknownArgumentType

    def has_write_access(self, user: User) -> bool:
        try:
            if user == self.lead:
                return True
        except ObjectDoesNotExist:
            pass
        return user.is_superuser  # type: ignore reportUnknownMemberType


class Box(models.Model):
    number: "models.IntegerField[Any, Any]" = models.IntegerField(primary_key=True)


class Mouse(models.Model):
    sex_choices = {
        "F": "Female",
        "M": "Male",
    }
    project: models.ForeignKey[Any, Any] = models.ForeignKey(
        Project, on_delete=models.PROTECT
    )
    sex: "models.CharField[Any, Any]" = models.CharField(
        max_length=1, choices=sex_choices
    )
    mother: models.ForeignKey[Any, Any] = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="child_set_m",
    )
    father: models.ForeignKey[Any, Any] = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="child_set_f",
    )
    date_of_birth: "models.DateField[Any, Any]" = models.DateField()
    tube_number: "models.IntegerField[Any, Any]" = models.IntegerField()
    box: "models.ForeignKey[Any, Any]" = models.ForeignKey(
        Box, on_delete=models.PROTECT
    )
    # TODO(moth): Do we need restricted choices here?
    strain: "models.TextField[Any, Any]" = models.TextField()
    # TODO(moth): Do we need restricted choices here?
    coat_colour: "models.TextField[Any, Any]" = models.TextField()
    # TODO(moth): Is this correct?
    earmark: "models.TextField[Any, Any]" = models.TextField()
    notes: "models.TextField[Any, Any]" = models.TextField()

    class Meta:
        permissions = [
            ("edit_mice", "Can edit mouse details"),
        ]

    def has_read_access(self, user: User) -> bool:
        return self.project.has_read_access(user) or user.has_perm("mouseapp.edit_mice")

    def has_write_access(self, user: User) -> bool:
        return self.project.has_write_access(user) or user.has_perm(
            "mouseapp.edit_mice"
        )


class Request(models.Model):
    BREED_REQUEST = "B"
    CULL_REQUEST = "C"
    REQUEST_CHOICES = {
        BREED_REQUEST: "Breed",
        CULL_REQUEST: "Cull",
    }

    creator: models.ForeignKey[Any, Any] = models.ForeignKey(
        User, on_delete=models.PROTECT
    )
    approver: models.ForeignKey[Any, Any] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_set",
    )
    approved_date: "models.DateField[Any, Any]" = models.DateField(
        blank=True, null=True
    )
    fulfill_date: "models.DateField[Any, Any]" = models.DateField(blank=True, null=True)
    kind: "models.CharField[Any, Any]" = models.CharField(
        max_length=1, choices=REQUEST_CHOICES
    )
    # TODO(moth): Do we need something more structured here?
    details: "models.TextField[Any, Any]" = models.TextField()

    class Meta:
        permissions = [
            ("approve_request", "Can approve requests"),
            ("fulfill_request", "Can mark requests fulfilled"),
        ]


class Membership(models.Model):
    project: models.ForeignKey[Any, Any] = models.ForeignKey(
        Project, on_delete=models.CASCADE
    )
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    permissions: "models.TextField[Any, Any]" = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_membership"
            )
        ]
