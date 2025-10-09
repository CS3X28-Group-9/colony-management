from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    lead = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="leading_set",
    )
    researchers = models.ManyToManyField(
        User, through="Membership", through_fields=("project", "user")
    )
    license_constraints = models.TextField()

    class Meta:
        permissions = [("create_project", "Create projects")]


class Box(models.Model):
    number = models.IntegerField(primary_key=True)


class Mouse(models.Model):
    sex_choices = {
        "F": "Female",
        "M": "Male",
    }
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    sex = models.CharField(max_length=1, choices=sex_choices)
    mother = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="child_set_m",
    )
    father = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="child_set_f",
    )
    date_of_birth = models.DateField()
    tube_number = models.IntegerField()
    box = models.ForeignKey(Box, on_delete=models.PROTECT)
    # TODO(moth): Do we need restricted choices here?
    strain = models.TextField()
    # TODO(moth): Do we need restricted choices here?
    coat_colour = models.TextField()
    # TODO(moth): Is this correct?
    earmark = models.TextField()
    notes = models.TextField()

    class Meta:
        permissions = [
            ("edit_mice", "Can edit mouse details"),
        ]


class Request(models.Model):
    BREED_REQUEST = "B"
    CULL_REQUEST = "C"
    REQUEST_CHOICES = {
        BREED_REQUEST: "Breed",
        CULL_REQUEST: "Cull",
    }

    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_set",
    )
    approved_date = models.DateField(blank=True, null=True)
    fulfill_date = models.DateField(blank=True, null=True)
    kind = models.CharField(max_length=1, choices=REQUEST_CHOICES)
    # TODO(moth): Do we need something more structured here?
    details = models.TextField()

    class Meta:
        permissions = [
            ("approve_request", "Can approve requests"),
            ("fulfill_request", "Can mark requests fulfilled"),
        ]


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permissions = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_membership"
            )
        ]
