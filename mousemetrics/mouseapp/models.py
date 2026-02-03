from django.db import models
from django.db.models import SET_NULL
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.urls import reverse


class Project(models.Model):
    id: int
    name = models.TextField()
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

    def __str__(self) -> str:
        return f"{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("mouseapp:project", args=[self.id])


class StudyPlan(models.Model):
    STATUS_CHOICES = {
        "D": "Draft",
        "S": "Submitted",
        "A": "Approved",
        "C": "Completed",
    }
    SOURCE_CHOICES = {
        "I": "Internal",
        "E": "External",
    }

    id: int
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_study_plans",
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="Draft")
    study_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    approval_date = models.DateField(blank=True, null=True)

    description = models.TextField(blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    mouse_quota_male = models.IntegerField(blank=True, null=True)
    mouse_quota_female = models.IntegerField(blank=True, null=True)
    mouse_source = models.CharField(
        max_length=1,
        choices=SOURCE_CHOICES,
        blank=True,
        null=True,
    )

    class Meta:
        permissions = [
            ("approve_study_plan", "Can approve a study plan"),
            ("view_study_plan", "Can view study plans"),
        ]

    def __str__(self) -> str:
        return f"Study plan for {self.project.name}"


class Box(models.Model):
    LOCATION_CHOICES = {"B": "Breeding", "E": "Experimental"}
    BOX_TYPE_CHOICES = {"S": "Shoe", "T": "Stock"}

    box_type = models.CharField(max_length=1, choices=BOX_TYPE_CHOICES, default="S")
    location = models.CharField(
        max_length=1,
        choices=LOCATION_CHOICES,
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=True, blank=True
    )
    number = models.TextField()

    class Meta:
        verbose_name_plural = "Boxes"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"], name="uniq_box_per_project"
            )
        ]

    def __str__(self) -> str:
        return f"Box {self.number}"


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

    id: int
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="mice_assigned",
    )
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
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
    cull_date = models.DateField(blank=True, null=True)
    cull_reason = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True)

    child_set_m: models.Manager
    child_set_f: models.Manager

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

    def descendant_depth(self) -> int:
        children = list(self.child_set_m.all()) + list(self.child_set_f.all())
        if not children:
            return 0
        return 1 + max(child.descendant_depth() for child in children)

    def has_read_access(self, user: User) -> bool:
        return self.project.has_read_access(user) or user.has_perm("mouseapp.edit_mice")

    def has_write_access(self, user: User) -> bool:
        return self.project.has_write_access(user) or user.has_perm(
            "mouseapp.edit_mice"
        )

    def __str__(self) -> str:
        return f"{self.strain} {self.tube_number}"

    def get_absolute_url(self) -> str:
        return reverse("mouseapp:mouse", args=[self.id])


class Request(models.Model):
    _user: User | None = None
    REQUEST_CHOICES = {
        "B": "Set up breeding pair",
        "C": "Cull",
        "T": "Transfer",
        "Q": "Query",
    }
    STATUS_CHOICES = {
        "P": "Pending",
        "A": "Accepted",
        "D": "Denied",
        "C": "Completed",
    }

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="requests",
        null=True,
        blank=True,
    )
    mouse = models.ForeignKey(
        Mouse, on_delete=models.CASCADE, related_name="requests", null=True, blank=True
    )
    creator = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_requests"
    )
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
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("approve_request", "Can approve requests"),
            ("fulfill_request", "Can mark requests fulfilled"),
        ]
        ordering = ["-created_at"]

    def can_change_status(self, user: User) -> bool:
        if user.is_superuser:
            return True

        if self.mouse and not self.mouse.has_read_access(user):
            return False
        if self.project and not self.project.has_read_access(user):
            return False

        if self.status == "P":
            if self.project and self.project.lead and self.project.lead.id == user.pk:
                return True
            if user.has_perm("mouseapp.approve_request"):
                return True
            return False
        return user.has_perm("mouseapp.approve_request")

    @property
    def user_can_change_status(self) -> bool:
        assert self._user is not None
        return self.can_change_status(self._user)

    def __str__(self) -> str:
        kind_display = dict(Request.REQUEST_CHOICES).get(self.kind, self.kind)
        return f"{kind_display} request from {self.creator}"


class RequestReply(models.Model):
    request = models.ForeignKey(
        Request, on_delete=models.CASCADE, related_name="replies"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("send_reply", "Can send replies and queries on requests")]

    def __str__(self) -> str:
        return f"Response to {self.request}"


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_membership"
            )
        ]

    def __str__(self) -> str:
        return f"{self.project}, {self.user}"


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
