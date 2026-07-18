from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from apps.reconciliation.filters import filters_reconciliation_result
from apps.reports.exporters import export_to_excel


def _save_copy_to_exports(filename: str, content: bytes) -> None:
    settings.EXPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    (settings.EXPORTS_ROOT / filename).write_bytes(content)

def export_excel(request):
    queryset = filters_reconciliation_result(request.GET)
    content = export_to_excel(queryset)

    filename = f"reconciliation_{timezone.localtime().strftime("%Y%m%d_%H%M%S")}.xlsx"
    _save_copy_to_exports(filename, content)

    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"

    return response
