from datetime import datetime

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.reconciliation.engine import run_reconciliation
from apps.reconciliation.models import ReconciliationResult
from apps.uploads.models import UploadedFile


def _resume_conciliation() -> dict:
    counts_qs = ReconciliationResult.objects.values("status").annotate(total=Count("id"))
    counts = {row["status"]: row["total"] for row in counts_qs}

    return {
        "total": ReconciliationResult.objects.count(),
        "conciliado": counts.get(ReconciliationResult.Status.CONCILIADO, 0),
        "divergencia": counts.get(ReconciliationResult.Status.DIVERGENCIA, 0),
        "nao_encontrado": counts.get(ReconciliationResult.Status.NAO_ENCONTRADO, 0),
        "possivel_duplicado": counts.get(ReconciliationResult.Status.POSSIVEL_DUPLICADO, 0),
    }

def home(request):
    context = {
        "total_arquivos": UploadedFile.objects.count(),
        "resumo": _resume_conciliation()
    }

    return render(request, "dashboard/home.html", context)

class ReconciliationResultListView(ListView):
    model = ReconciliationResult
    template_name = "dashboard/result_list.html"
    context_object_name = "resultados"
    paginate_by = 20

    def _parse_date(self, value):
        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def get_queryset(self):
        qs = ReconciliationResult.objects.select_related("receivable", "bank_transaction").order_by(
            "receivable__due_date", "receivable__client_name"
        )

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        cliente = self.request.GET.get("cliente")
        if cliente:
            qs = qs.filter(receivable__client_name__icontains=cliente)

        data_inicio = self._parse_date(self.request.GET.get("data_inicio"))
        if data_inicio:
            qs = qs.filter(receivable__due_date__gte=data_inicio)

        data_fim = self._parse_date(self.request.GET.get("data_fim"))
        if data_fim:
            qs = qs.filter(receivable__due_date__lte=data_fim)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = ReconciliationResult.Status.choices
        context["filtros"] = {
            "status": self.request.GET.get("status", ""),
            "cliente": self.request.GET.get("cliente", ""),
            "data_inicio": self.request.GET.get("data_inicio", ""),
            "data_fim": self.request.GET.get("data_fim", ""),
        }
        context["resumo"] = _resume_conciliation()

        params = self.request.GET.copy()
        params.pop("page", None)
        context["querystring"] = params.urlencode()

        return context