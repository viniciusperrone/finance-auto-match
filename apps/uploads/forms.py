from django import forms

from core.utils.file_validation import validate_upload_file

from .models import UploadedFile


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["file_type", "file"]
        widgets = {
            "file_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv,.xlsx,.xls"}),
        }
        labels = {
            "file_type": "Tipo de arquivo",
            "file": "Arquivo (.csv, .xlsx, .xls)"
        }

    def clean_file(self):
        file = self.cleaned_data["file"]
        validate_upload_file(file)

        return file
