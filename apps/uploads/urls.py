from django.urls import path

from . import views

app_name = 'uploads'

urlpatterns = [
    path("", views.UploadedFileListView.as_view(), name="list"),
    path("new/", views.UploadedFileCreateView.as_view(), name="create"),
    path("<int:pk>/delete", views.UploadedFileDeleteView.as_view(), name="delete"),
]
