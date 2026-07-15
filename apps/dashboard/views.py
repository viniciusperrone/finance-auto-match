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
