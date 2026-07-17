import json
from datetime import datetime
from openpyxl import Workbook
from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.reconciliation.engine import run_reconciliation
from apps.reconciliation.models import ReconciliationResult
from apps.uploads.models import UploadedFile

Status = ReconciliationResult.Status

def _resume_conciliation() -> dict:
    counts_qs = ReconciliationResult.objects.values("status").annotate(
        total=Count("id"), value=Sum("receivable__expected_amount")
    )
    by_status = {row["status"]: row for row in counts_qs}

    def count_for(status):
        return by_status.get(status, {}).get("total", 0)

    def value_for(status):
        return float(by_status.get(status, {}).get("valor") or Decimal("0.00"))

    return {
        "total": ReconciliationResult.objects.count(),
        "reconciled": count_for(Status.CONCILIADO),
        "discrepancy": count_for(Status.DIVERGENCIA),
        "not_found": count_for(Status.NAO_ENCONTRADO),
        "possible_duplicate": count_for(Status.POSSIVEL_DUPLICADO),
        "values": {
            "reconciled": value_for(Status.CONCILIADO),
            "discrepancy": value_for(Status.DIVERGENCIA),
            "not_found": value_for(Status.NAO_ENCONTRADO),
            "possible_duplicate": value_for(Status.POSSIVEL_DUPLICADO)
        }
    }

def home(request):
    resume = _resume_conciliation()
    context = {
        "all_files": UploadedFile.objects.count(),
        "resume": resume,
        "chart_status_counts": json.dumps(
            {
                "Conciliado": resume["reconciled"],
                "Divergência": resume["discrepancy"],
                "Não encontrado": resume["not_found"],
                "Possível duplicado": resume["possible_duplicate"],
            }
        ),
        "chart_status_values": json.dumps(
            {
                "Conciliado": round(resume["values"]["reconciled"], 2),
                "Divergência": round(resume["values"]["discrepancy"], 2),
                "Não encontrado": round(resume["values"]["not_found"], 2),
                "Possível duplicado": round(resume["values"]["possible_duplicate"], 2),
            }
        ),
    }

    return render(request, "dashboard/home.html", context)

class ReconciliationResultListView(ListView):
    model = ReconciliationResult
    template_name = "dashboard/results_list.html"
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

class ReconciliationResultDetailReview(DetailView):
    model = ReconciliationResult
    template_name = "dashboard/results_detail.html"
    context_object_name = "resultado"

@require_POST
def recalculate(request):
    summary = run_reconciliation()
    messages.success(
        request,
        f"Conciliação recalculada: {summary['conciliado']} conciliado(s), "
        f"{summary['divergencia']} divergência(s), {summary['nao_encontrado']} não encontrado(s), "
        f"{summary['possivel_duplicado']} possível(is) duplicado(s).",
    )
    next_url = request.META.get("HTTP_REFERER")

    return redirect(next_url or "dashboard:home")

def export_results_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Resultado da Conciliação"

    worksheet.append([
        "Cliente",
        "Valor Esperado",
        "Valor Recebido",
        "Status",
        "Score",
        "Diferença",
        "Diferença (dias)",
        "Observações",
    ])

    results = (
        ReconciliationResult.objects
        .select_related("receivable", "bank_transaction")
        .order_by("receivable__client_name")
    )

    for result in results:
        worksheet.append([
            result.receivable.client_name,
            float(result.receivable.expected_amount),
            float(result.bank_transaction.amount) if result.bank_transaction else "",
            result.get_status_display(),
            float(result.score),
            float(result.amount_difference) if result.amount_difference is not None else "",
            result.date_difference_days if result.date_difference_days is not None else "",
            result.notes,
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="resultado_conciliacao.xlsx"'
    )

    workbook.save(response)

    return response
