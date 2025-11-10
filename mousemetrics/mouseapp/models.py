from django.db import models
from django.db.models import SET_NULL
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Project(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateField()
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
    researchers = models.ManyToManyField(
        User, through="Membership", through_fields=("project", "user")
    )
    license_constraints = models.TextField()

    class Meta:
        permissions = [("create_project", "Create projects")]
        ordering = ["name"]

    def has_read_access(self, user: User) -> bool:
        if self.lead and self.lead.pk == user.pk:
            return True
        if user.is_superuser:
            return True
        return self.researchers.filter(pk=user.pk).exists()

    def has_write_access(self, user: User) -> bool:
        if self.lead and self.lead.pk == user.pk:
            return True
        return user.is_superuser

    def mouse_count(self):
        return self.mouse_set.count()  # type: ignore


class StudyPlan(models.Model):
    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Submitted", "Submitted"),
        ("Approved", "Approved"),
        ("Completed", "Completed"),
    )
    SOURCE_CHOICES = {
        "I": "Internal",
        "E": "External",
    }

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_study_plans",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Draft")
    study_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    approval_date = models.DateField(blank=True, null=True)

    description = models.TextField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    mouse_quota_male = models.IntegerField(blank=True, null=True)
    mouse_quota_female = models.IntegerField(blank=True, null=True)
    mouse_source = models.CharField(
        choices=SOURCE_CHOICES,
        blank=True,
        null=True,
    )

    class Meta:
        permissions = [
            ("approve_study_plan", "Can approve a study plan"),
            ("view_study_plan", "Can view study plans"),
        ]


class Box(models.Model):
    LOCATION_CHOICES = {"B": "Breeding", "E": "Experimental"}
    box_type = models.CharField(
        max_length=1, choices=[("S", "Shoe"), ("T", "Stock")], default="S"
    )
    location = models.CharField(
        max_length=1,
        choices=LOCATION_CHOICES,
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=True, blank=True
    )
    number = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Boxes"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"], name="uniq_box_per_project"
            )
        ]


class Strain(models.Model):
    name = models.TextField(unique=True)

    def __str__(self) -> str:
        return self.name


class Mouse(models.Model):
    SEX_CHOICES = {"F": "Female", "M": "Male"}

    EARMARK_VALIDATOR = RegexValidator(
        regex=r"^([TB][RL])*$",
        message="Earmark must be a sequence of position codes (T/B for Top/Bottom, R/L for Right/Left). Examples: TR, BL, TRBL.",
        code="invalid_earmark",
    )

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="mice_assigned",
    )
    sex = models.CharField(max_length=1, choices=list(SEX_CHOICES.items()))
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
    strain = models.ForeignKey(Strain, on_delete=models.PROTECT, null=True, blank=True)
    coat_colour = models.TextField(blank=True, null=True)
    earmark = models.CharField(
        max_length=16, blank=True, validators=[EARMARK_VALIDATOR]
    )
    notes = models.TextField(blank=True)

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

    def has_read_access(self, user: User) -> bool:
        return self.project.has_read_access(user) or user.has_perm("mouseapp.edit_mice")

    def has_write_access(self, user: User) -> bool:
        return self.project.has_write_access(user) or user.has_perm(
            "mouseapp.edit_mice"
        )


class Request(models.Model):
    REQUEST_CHOICES = (
        ("B", "Set up breeding pair"),
        ("C", "Cull"),
        ("T", "Transfer"),
        ("Q", "Query"),
    )

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="requests", null=True
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


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_membership"
            )
        ]
