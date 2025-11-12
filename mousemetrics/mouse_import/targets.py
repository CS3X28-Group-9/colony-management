from django.db.models import NOT_PROVIDED
from mouseapp.models import Mouse, Strain

EXCLUDE_FIELDS = {"id", "project"}  # project handled separately

FIELD_CHOICES = {
    "strain": lambda project: [
        (strain.name, strain.name) for strain in Strain.objects.all()
    ]
}


def get_mouse_import_targets(project):
    required, optional = [], []
    field_choices = {}

    for f in Mouse._meta.get_fields():
        # skip reverse / M2M / internal
        if (
            getattr(f, "many_to_many", False)
            or getattr(f, "one_to_many", False)
            or getattr(f, "auto_created", False)
        ):
            continue
        if not getattr(f, "editable", True):
            continue
        if f.name in EXCLUDE_FIELDS:
            continue

        label = getattr(f, "verbose_name", f.name).replace("_", " ").capitalize()
        has_default = getattr(f, "default", NOT_PROVIDED) is not NOT_PROVIDED
        required_flag = (
            not getattr(f, "null", False)
            and not getattr(f, "blank", False)
            and not has_default
        )
        (required if required_flag else optional).append((f.name, label))

        if choice_f := FIELD_CHOICES.get(f.name):
            field_choices[f.name] = choice_f(project)

    return sorted(required), sorted(optional), field_choices
