from django.urls import path

from apps.reports.views import export_excel, export_pdf

app_name = "reports"

urlpatterns = [
    path("excel/", export_excel, name="export_excel"),
    path("pdf/", export_pdf, name="export_pdf")
]
