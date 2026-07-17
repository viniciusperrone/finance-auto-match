from datetime import datetime

from apps.reconciliation.models import ReconciliationResult


def _parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def filters_reconciliation_result(params):
    qs = ReconciliationResult.objects.select_related("receivable", "bank_transaction").order_by(
        "receivable__due_date", "receivable__client_name"
    )

    status = params.get("status")
    if status:
        qs = qs.filter(status=status)

    client = params.get("cliente")
    if client:
        qs = qs.filter(receivable__client_name__icontains=client)

    start_date = _parse_date(params.get("data_inicio"))
    if start_date:
        qs = qs.filter(receivable__due_date__gte=start_date)

    end_date = _parse_date(params.get("data_fim"))
    if end_date:
        qs = qs.filter(receivable__due_date__lte=end_date)

    return qs
