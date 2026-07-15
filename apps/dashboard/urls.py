from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("resultados/", views.ReconciliationResultListView.as_view(), name="results_list"),
    path("resultados/<int:pk>/", views.ReconciliationResultDetailReview.as_view(), name="results_detail"),
]
