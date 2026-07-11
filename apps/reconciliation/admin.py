from django.contrib import admin

from .models import BankTransaction, ImportIssue, Receivable


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
