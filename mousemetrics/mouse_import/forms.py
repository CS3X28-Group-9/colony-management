from typing import Iterable

from django import forms

from .models import MouseImport
from .services.validators import normalise_cell_range
from .targets import get_mouse_import_targets


class MouseImportForm(forms.ModelForm):
    class Meta:
        model = MouseImport
        # Upload-only: sheet/range are selected.
        fields = ["project", "file"]


class MouseImportSheetRangeForm(forms.ModelForm):
    """Second-step form to capture sheet + cell_range."""

    # drop down for sheet names
    sheet_name = forms.ChoiceField(required=False)

    class Meta:
        model = MouseImport
        fields = ["sheet_name", "cell_range"]

    def __init__(self, *args, sheet_choices: list[str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sheet_choices = sheet_choices or []

        # Allow "(active)" via blank string.
        choices: list[tuple[str, str]] = [("", "(active)")] + [
            (s, s) for s in self._sheet_choices
        ]

        # If the instance already has a sheet_name that isn't in the detected list
        # (e.g. workbook read error), keep it selectable so form rendering/POSTs work.
        current = (getattr(self.instance, "sheet_name", "") or "").strip()
        if current and current not in self._sheet_choices:
            choices.append((current, current))

        sheet_field = self.fields["sheet_name"]
        # assign as list[tuple[str,str]] for stub-friendly typing
        sheet_field.widget.choices = [(str(a), str(b)) for a, b in choices]

        # Basic styling hooks for templates that render {{ field }} directly.
        sheet_field.widget.attrs.setdefault(
            "class",
            "block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
        )
        self.fields["cell_range"].widget.attrs.setdefault(
            "class",
            "block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
        )
        self.fields["cell_range"].widget.attrs.setdefault("placeholder", "e.g., A1:M40")

    def clean_sheet_name(self):
        sheet = (self.cleaned_data.get("sheet_name") or "").strip()
        sheet_field = self.fields["sheet_name"]
        if not isinstance(sheet_field, forms.ChoiceField):
            raise TypeError(
                "MouseImportSheetRangeForm expects 'sheet_name' to be a ChoiceField"
            )

        widget = sheet_field.widget
        if not hasattr(widget, "choices"):
            raise TypeError(
                "MouseImportSheetRangeForm expects 'sheet_name' widget to support 'choices'"
            )

        # widget.choices is an iterable of (value, label)
        allowed = {str(c) for c, _ in widget.choices}  # coerce to str for safety
        if sheet and sheet not in allowed:
            raise forms.ValidationError("Select a valid sheet.")
        return sheet

    def clean_cell_range(self):
        rng = (self.cleaned_data.get("cell_range") or "").strip()
        try:
            return normalise_cell_range(rng)
        except ValueError as exc:
            raise forms.ValidationError(str(exc))


class ColumnMappingForm(forms.Form):
    def __init__(
        self, *args, columns: Iterable[str] | None = None, project=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__project = project
        columns = list(columns or [])
        req, opt, field_choices = get_mouse_import_targets(project)

        # choices
        col_choices: list[tuple[str, str]] = [(c, c) for c in columns]
        targets: list[tuple[bool, str, str]] = [(True, *r) for r in req] + [
            (False, *o) for o in opt
        ]

        for required, name, label in targets:
            choices_for_field = field_choices.get(name)

            # build choices list as list[tuple[str, str]] for type-friendliness, coercing to str for safety
            base_choices: list[tuple[str, str]] = col_choices + (
                [("", "-- none --")] if not required else []
            )
            if choices_for_field:
                base_choices = base_choices + [("-- fixed --", "-- fixed --")]

            self.fields[f"map_{name}"] = forms.ChoiceField(
                label=label,
                choices=[(str(a), str(b)) for a, b in base_choices],
                required=required,
            )

            if choices_for_field:
                self.fields[f"fixed_{name}"] = forms.ChoiceField(
                    label=f"Value for {label}",
                    choices=[(str(a), str(b)) for a, b in choices_for_field],
                    widget=forms.Select(attrs={"data-choices-for": f"{name}"}),
                )
                if ("-- new --", "-- new --") in choices_for_field:
                    self.fields[f"fixed_new_{name}"] = forms.CharField(
                        label=f"Value for {label}",
                        required=False,
                    )

    def selected_mapping(self):
        req, opt, field_choices = get_mouse_import_targets(self.__project)
        mapping: dict[str, str] = {}
        fixed: dict[str, str] = {}
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
