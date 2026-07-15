from django.contrib import admin

from .models import BankTransaction, ImportIssue, Receivable, ReconciliationResult


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'description', 'amount', "uploaded_file", "row_number")
    list_filter = ('uploaded_file',)
    search_fields = ("description", "description_normalized")
    date_hierarchy = "transaction_date"


@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    list_display = ("client_name", "due_date", "expected_amount", "document_number", "uploaded_file", "row_number")
    list_filter = ("uploaded_file",)
    search_fields = ("client_name", "client_name_normalized", "document_number")
    date_hierarchy = "due_date"

@admin.register(ImportIssue)
class ImportIssueAdmin(admin.ModelAdmin):
    list_display = ("uploaded_file", "row_number", "error_message", "created_at")
    list_filter = ("uploaded_file",)
    readonly_fields = ("uploaded_file", "row_number", "raw_row", "error_message", "created_at")

@admin.register(ReconciliationResult)
class ReconciliationResultAdmin(admin.ModelAdmin):
    list_display = ("receivable", "status", "score", "bank_transaction", "amount_difference", "date_difference_days")
    list_filter = ("status",)
    search_fields = ("receivable__client_name", "notes")
    readonly_fields = (
        "receivable", "bank_transaction", "status", "score", "amount_difference",
        "date_difference_days", "notes", "candidates_considered", "created_at", "updated_at",
    )
