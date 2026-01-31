from django import forms
from .models import MouseImport
from .targets import get_mouse_import_targets
from typing import List


class MouseImportForm(forms.ModelForm):
    class Meta:
        model = MouseImport
        fields = ["project", "file", "sheet_name", "cell_range"]

    def clean_cell_range(self):
        rng = self.cleaned_data["cell_range"].strip()
        if ":" not in rng:
            raise forms.ValidationError('Enter a range like "A1:M40"')
        return rng


class ColumnMappingForm(forms.Form):
    def __init__(self, *args, columns=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__project = project
        columns = columns or []
        req, opt, field_choices = get_mouse_import_targets(project)

        # choices
        col_choices = [(c, c) for c in columns]
        targets: list[tuple[bool, str, str]] = [(True, *r) for r in req] + [
            (False, *o) for o in opt
        ]

        for required, name, label in targets:
            choices = field_choices.get(name)

            self.fields[f"map_{name}"] = forms.ChoiceField(
                label=label,
                choices=col_choices
                + ([("", "-- none --")] if not required else [])
                + ([("-- fixed --", "-- fixed --")] if choices else []),
                required=required,
            )

            if choices:
                self.fields[f"fixed_{name}"] = forms.ChoiceField(
                    label=f"Value for {label}",
                    choices=choices,
                    widget=forms.Select(attrs={"data-choices-for": f"{name}"}),
                )
                if ("-- new --", "-- new --") in choices:
                    self.fields[f"fixed_new_{name}"] = forms.CharField(
                        label=f"Value for {label}",
                        required=False,
                    )

    def selected_mapping(self):
        req, opt, field_choices = get_mouse_import_targets(self.__project)
        mapping = {}
        fixed = {}
        for name, _ in req + opt:
            mapping[name] = self.cleaned_data.get(f"map_{name}", "") or ""
            if name in field_choices and mapping[name] == "-- fixed --":
                if (fixed_val := self.cleaned_data.get(f"fixed_{name}", "")) or "":
                    if fixed_val == "-- new --":
                        fixed[name] = (
                            self.cleaned_data.get(f"fixed_new_{name}", "") or ""
                        )
                    else:
                        fixed[name] = fixed_val

        return self.cleaned_data, fixed, mapping
