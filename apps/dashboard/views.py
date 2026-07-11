from django.shortcuts import render

from apps.uploads.models import UploadedFile


def home(request):
    context = {
        "total_arquivos": UploadedFile.objects.count(),
    }

    return render(request, "dashboard/home.html", context)
