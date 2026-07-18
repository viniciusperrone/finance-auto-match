import io
from collections import Counter

from django.db.models import QuerySet
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.reconciliation.models import ReconciliationResult


Status = ReconciliationResult.Status
STATUS_LABELS = dict(Status.choices)

HEADER_BG_HEX = "1F2937"
STATUS_BG_HEX = {
    Status.CONCILIADO: "D1FAE5",
    Status.DIVERGENCIA: "FEF3C7",
    Status.NAO_ENCONTRADO: "E5E7EB",
    Status.POSSIVEL_DUPLICADO: "FEE2E2",
}

def build_summary(queryset) -> dict:
    counts = Counter(queryset.values_list("status", flat=True))

    return {
        "total": sum(counts.values()),
        "reconciled": counts.get(Status.CONCILIADO, 0),
        "discrepancy": counts.get(Status.DIVERGENCIA, 0),
        "not_found": counts.get(Status.NAO_ENCONTRADO, 0),
        "possible_duplicate": counts.get(Status.POSSIVEL_DUPLICADO, 0)
    }

def export_to_excel(queryset: QuerySet[ReconciliationResult]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Conciliação"

    headers = [
        "Cliente", "Documento", "Vencimento", "Valor esperado", "Status",
        "Score", "Transação encontrada", "Data da transação",
        "Valor da transação", "Diferença de valor", "Diferença de data (dias)",
        "Observações", "Arquivos de origem"
    ]
    ws.append(headers)
    header_fill = PatternFill(start_color=HEADER_BG_HEX, end_color=HEADER_BG_HEX, fill_type="solid")

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")

    row_idx = 2
    for result in queryset.select_related("receivable", "bank_transaction", "receivable__uploaded_file"):
        receivable = result.receivable
        transaction = result.bank_transaction

        ws.append([
            receivable.client_name,
            receivable.document_number,
            receivable.due_date,
            float(receivable.expected_amount),
            STATUS_LABELS.get(result.status, result.status),
            float(result.score),
            transaction.description if transaction else "",
            transaction.transaction_date if transaction else None,
            float(transaction.amount) if transaction else None,
            float(result.amount_difference) if result.amount_difference is not None else None,
            result.date_difference_days,
            result.notes,
            receivable.uploaded_file.original_filename
        ])

        fill_hex = STATUS_BG_HEX.get(result.status)
        if fill_hex:
            fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = fill
        for col_idx in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col_idx).font = Font(name="Arial", size=10)
        row_idx += 1

    last_row = row_idx - 1
    for col in (3, 8):
        for row in range(2, row_idx):
            ws.cell(row=row, column=col).number_format = "DD/MM/YYYY"

    for col in (4, 9, 10):
        for row in range(2, row_idx):
            ws.cell(row=row, column=col).number_format = "#,##0.00"

    widths = [24, 14, 12, 14, 22, 8, 14, 14, 14, 12, 50, 26]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    if last_row >= 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last_row}"

    ws2 = wb.create_sheet("Resumo")
    ws2.append(["Indicador", "Valor"])
    for col in ("A", "B"):
        ws2[f"{col}1"].font = Font(name="Arial", bold=True, color="FFFFFF")
        ws2[f"{col}1"].fill = header_fill

    if last_row >= 2:
        resume_rows = [
            ("Total de registros processados", f"=COUNTA('Conciliação'!A2:A{last_row})"),
            ("Total conciliado", f"=COUNTIF('Conciliação'!E2:E{last_row},\Conciliado\")"),
            ("Total com divergência", f"=COUNTIF('Conciliação'!E2:E{last_row},\Divergência\")"),
            ("Total pendente (não encontro)", f"=COUNTIF('Conciliação'!E2:E{last_row},\Pagamento não encontrado\")"),
            ("Possíveis duplicidades", f"=COUNTIF('Conciliação'!E2:E{last_row},\Possível pagamento duplicado\")")
        ]

    else:
        summary = build_summary(queryset)
        resume_rows = [
            ("Total de registros processados", summary["total"]),
            ("Total conciliado", summary["reconciled"]),
            ("Total com divergência", summary["discrepancy"]),
            ("Total pendente (não encontrado)", summary["not_found"]),
            ("Possíveis duplicidades", summary["possible_duplicate"]),
        ]

    resume_rows.append(("Gerado em", timezone.localtime().strftime("%d/%m/%Y %H:%M")))

    for label, value in resume_rows:
        ws2.append([label, value])

    for row in range(2, len(resume_rows) + 2):
        ws2.cell(row=row, column=1).font = Font(name="Arial", size=10)
        ws2.cell(row=row, column=2).font = Font(name="Arial", size=10)

    ws2.column_dimensions["A"].width = 34
    ws2.column_dimensions["B"].width = 20

    buffer = io.BytesIO()
    wb.save(buffer)

    return buffer.getvalue()
