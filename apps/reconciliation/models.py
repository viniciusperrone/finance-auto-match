from django.db import models

from apps.uploads.models import UploadedFile


class BankTransaction(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile, on_delete=models.CASCADE, related_name="bank_transactions"
    )
    row_number = models.PositiveIntegerField(
        help_text="Número da linha no arquivo."
    )
    transaction_date = models.DateField()
    description = models.CharField(max_length=500)
    description_normalized = models.CharField(
        max_length=500,
        db_index=True,
        help_text="Descrição sem acentos, maiúscula e sem espaços duplicados, usada na conciliação."
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    raw_data = models.JSONField(default=dict, blank=True, help_text="Linha original do arquivo, para auditoria.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["transaction_date", "id"]
        indexes = [
            models.Index(fields=["transaction_date"]),
            models.Index(fields=["amount"]),
        ]
        verbose_name = "Transação do extrato"
        verbose_name_plural = "Transações do extrato"

    def __str__(self) -> str:
        return f"{self.transaction_date} | {self.description} | R$ {self.amount}"

class Receivable(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile, on_delete=models.CASCADE, related_name="receivables"
    )
    row_number = models.PositiveIntegerField(help_text="Número da linha no arquivo.")
    client_name = models.CharField(max_length=255)
    client_name_normalized = models.CharField(max_length=255, db_index=True)
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=14, decimal_places=2)
    document_number = models.CharField(max_length=100, blank=True)
    raw_data = models.JSONField(default=dict, blank=True, help_text="Linha original do arquivo, para auditoria.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "id"]
        indexes = [
            models.Index(fields=["due_date"]),
            models.Index(fields=["expected_amount"]),
            models.Index(fields=["document_number"]),
        ]
        verbose_name = "Conta a receber"
        verbose_name_plural = "Contas a receber"

    def __str__(self) -> str:
        return f"{self.client_name} | venc {self.due_date} | R$ {self.expected_amount}"

class ImportIssue(models.Model):
    uploaded_file = models.ForeignKey(
        UploadedFile, on_delete=models.CASCADE, related_name="import_issues"
    )
    row_number = models.PositiveIntegerField()
    raw_row = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_file", "row_number"]
        verbose_name = "Problema de importação"
        verbose_name_plural = "Problemas de importação"

    def __str__(self) -> str:
        return f"Linha {self.row_number}: {self.error_message}"

class ReconciliationResult(models.Model):

    class Status(models.TextChoices):
        CONCILIADO = "conciliado", "Conciliado"
        DIVERGENCIA = "divergencia", "Divergência"
        NAO_ENCONTRADO = "nao_encontrado", "Pagamento não encontrado"
        POSSIVEL_DUPLICADO = "possivel_duplicado", "Possível pagamento duplicado"

    receivable = models.OneToOneField(
        "reconciliation.Receivable", on_delete=models.CASCADE, related_name="reconciliation_result"
    )
    bank_transaction = models.ForeignKey(
        "reconciliation.BankTransaction",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reconciliation_results",
        help_text="Transação encontrada."
    )
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Índice de confiança da correspondência, de 0 a 100."
    )
    amount_difference = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
    )
    date_difference_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Diferença de dias entre a transação e o recebido"
    )
    notes = models.TextField(blank=True)
    candidates_considered = models.JSONField(
        default=list, blank=True,
        help_text="Até 5 melhores transações candidatas consideradas, para auditoria.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["receivable__due_date"]
        verbose_name = "Resultado da conciliação"
        verbose_name_plural = "Resultados da conciliação"

    def __str__(self) -> str:
        return f"{self.receivable} -> {self.get_status_display()} ({self.score})"
