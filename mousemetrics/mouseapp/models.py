from typing import Any
from django.db import models
from django.db.models import SET_NULL
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist


class Project(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    start_date = models.DateField(null=False, blank=False)
    allow_over_18_months = models.BooleanField(default=False)
    has_mod_sev_permission = models.BooleanField(default=False)
    quota_5_years = models.PositiveIntegerField(null=True, blank=True)

    lead = models.ForeignKey(
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

    def has_read_access(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(self, "lead_id", None) == user.id:
            return True
        if getattr(user, "is_superuser", False):
            return True
        return self.researchers.filter(id=user.id).exists()

    def has_write_access(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(self, "lead_id", None) == user.id:
            return True
        return getattr(user, "is_superuser", False)


class Box(models.Model):
    id = models.BigAutoField(primary_key=True)
    box_type = models.CharField(
        max_length=1, choices=[("S", "Shoe"), ("T", "Stock")], default="S"
    )
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    number = models.IntegerField()

    class Meta:
        verbose_name_plural = "Boxes"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"], name="uniq_box_per_project"
            )
        ]


class Mouse(models.Model):
    EARMARK_VALIDATOR = RegexValidator(
        regex=r"^([TB][RL])*$",
        message="Earmark must follow the pattern ([TB][RL])* (e.g., TRBL, TRTR, BLBL).",
        code="invalid_earmark",
    )
    SEX_CHOICES = [("F", "Female"), ("M", "Male")]

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    mother = models.ForeignKey(
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
    date_of_birth = models.DateField()
    tube_number = models.IntegerField()
    box = models.ForeignKey(Box, on_delete=models.PROTECT)
    strain = models.TextField()
    coat_colour = models.TextField()
    earmark = models.CharField(
        max_length=16, blank=True, validators=[EARMARK_VALIDATOR]
    )
    notes = models.TextField()

    def clean(self):
        if (
            self.project
            and self.date_of_birth
            and not self.project.allow_over_18_months
        ):
            if self.date_of_birth < (now().date() - timedelta(days=548)):
                raise ValidationError(
                    {
                        "date_of_birth": "Project does not permit mice older than 18 months."
                    }
                )

    class Meta:
        permissions = [
            ("edit_mice", "Can edit mouse details"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "strain", "tube_number"],
                name="unique_mouse_id_per_project",
            )
        ]

    def has_read_access(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return self.project.has_read_access(user) or user.has_perm("mouseapp.edit_mice")

    def has_write_access(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return self.project.has_write_access(user) or user.has_perm(
            "mouseapp.edit_mice"
        )


class Request(models.Model):
    REQUEST_CHOICES = [
        ("B", "Set up breeding pair"),
        ("C", "Cull"),
        ("T", "Transfer"),
        ("Q", "BW Health Query"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="requests"
    )
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
    details = models.TextField()

    class Meta:
        permissions = [
            ("approve_request", "Can approve requests"),
            ("fulfill_request", "Can mark requests fulfilled"),
        ]


class RequestReply(models.Model):
    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name="replies"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("send_reply", "Can send replies and queries on requests")]


class Role(models.TextChoices):
    LEAD = "LEAD", "Lead"
    BREEDING = "BREEDING", "Breeding"
    READER = "READER", "Reader"


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role, default=Role.READER)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_membership"
            )
        ]


class StudyPlan(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, default="Draft")
    study_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    description = models.TextField()
    approval_date = models.DateField(blank=True, null=True)

    class Meta:
        permissions = [
            ("approve_study_plan", "Can approve a study plan"),
            ("view_study_plan", "Can view study plans"),
        ]
