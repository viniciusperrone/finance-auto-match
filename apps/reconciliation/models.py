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
