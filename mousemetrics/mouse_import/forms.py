from django import forms
from .models import MouseImport
from .targets import get_mouse_import_targets


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
    def __init__(self, *args, columns=None, **kwargs):
        super().__init__(*args, **kwargs)
        columns = columns or []
        req, opt = get_mouse_import_targets()

        # choices
        col_choices_req = [(c, c) for c in columns]
        col_choices_opt = [("", "-- none --")] + [(c, c) for c in columns]

        for name, label in req:
            self.fields[f"map_{name}"] = forms.ChoiceField(
                label=label, choices=col_choices_req
            )
        for name, label in opt:
            self.fields[f"map_{name}"] = forms.ChoiceField(
                label=label, choices=col_choices_opt, required=False
            )

    def selected_mapping(self):
        req, opt = get_mouse_import_targets()
        mapping = {}
        for name, _ in req + opt:
            mapping[name] = self.cleaned_data.get(f"map_{name}", "") or ""
        return mapping
