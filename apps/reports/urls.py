from django.urls import path

from apps.reports.views import export_excel

app_name = "reports"

urlpatterns = [
    path("excel/", export_excel, name="export_excel"),
]
