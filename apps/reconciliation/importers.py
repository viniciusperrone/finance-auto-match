from dataclasses import dataclass, field
import pandas as pd
from django.db import transaction


from core.utils.normalization import (
    normalize_amount,
    normalize_column_name,
    normalize_date,
    normalize_text
)

from .models import BankTransaction, ImportIssue, Receivable


@dataclass
class ImportResult:
    total_rows: int = 0
    imported: int = 0
    failed: int = 0
    errors: list = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return self.total_rows > 0

class BaseImporter:
    model = None
    required_columns: set[str] = set()

    def read_dataframe(self, file_field) -> pd.DataFrame:
        name = file_field.name.lower()
        file_field.open("rb")

        try:
            if name.endswith(".csv"):
                df = pd.read_csv(file_field, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            elif name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_field, dtype=str)
                df = df.fillna("")
            else:
                raise ValueError(f"Extensão de arquivo não suportada para importação: '{name}'")
        finally:
            file_field.close()

        df.columns = [normalize_column_name(c) for c in df.columns]

        return df

    def validate_columns(self, df: pd.DataFrame) -> None:
        missing = self.required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"Colunas obrigatórias ausentes no arquivo: {', '.join(sorted(missing))}. "
                f"Colunas encontradas: {', '.join(df.columns)}."
            )

    def parse_row(self, row: "pd.Series") -> dict:
        raise NotImplementedError

    def build_instance(self, uploaded_file, row_number: int, parsed: dict):
        raise NotImplementedError

    def import_file(self, uploaded_file) -> ImportResult:
        result = ImportResult

        df = self.read_dataframe(uploaded_file.file)
        self.validate_columns(df)
        result.total_rows = len(df)

        instances = []
        issues = []

        for position, row in df.iterrows():
            row_number = position + 2

            try:
                parsed = self.parse_row(row)
                instances.append(self.build_instance(uploaded_file, row_number, parsed))
                result.imported += 1
            except Exception as exc:
                result.failed += 1
                result.errors.append({"row": row_number, "message": str(exc)})
                issues.append(
                    ImportIssue(
                        uploaded_file=uploaded_file,
                        row_number=row_number,
                        raw_row=row.to_dict(),
                        error_message=str(exc),
                    )
                )

        with transaction.atomic():
            self.model.objects.filter(uploaded_file=uploaded_file).delete()
            ImportIssue.objects.filter(uploaded_file=uploaded_file).delete()

            if instances:
                self.model.objects.bulk_create(instances)
            if issues:
                ImportIssue.objects.bulk_create(issues)

        return result

class BankStatementImporter(BaseImporter):
    model = BankTransaction
    required_columns = {"data", "descricao", "valor"}

    def parse_row(self, row) -> dict:
        raw_description = row.get("descricao")

        if not str(raw_description or "").strip():
            raise ValueError("Descrição vazia")

        return {
            "transaction_date": normalize_date(row.get("data")),
            "description": str(raw_description).strip(),
            "description_normalized": normalize_text(raw_description),
            "amount": normalize_amount(row.get("valor")),
            "raw_data": row.to_dict(),
        }

    def build_instance(self, uploaded_file, row_number, parsed):
        return BankTransaction(uploaded_file=uploaded_file, row_number=row_number, **parsed)


class ReceivableImporter(BaseImporter):
    model = Receivable
    required_columns = {"cliente", "vencimento", "valor_esperado"}

    def parse_row(self, row) -> dict:
        raw_client = row.get("cliente")

        if not str(raw_client or "").strip():
            raise ValueError("Nome do cliente vazio")

        return {
            "client_name": str(raw_client).strip(),
            "client_name_normalized": normalize_text(raw_client),
            "due_date": normalize_date(row.get("vencimento")),
            "expected_amount": normalize_amount(row.get("valor_esperado")),
            "document_number": str(row.get("documento" or "")).strip(),
            "raw_data": row.to_dict(),
        }

    def build_instance(self, uploaded_file, row_number, parsed):
        return Receivable(uploaded_file=uploaded_file, row_number=row_number, **parsed)

def get_importer_for(uploaded_file) -> BaseImporter:
    from apps.uploads.models import UploadedFile

    importer_map = {
        UploadedFile.FileType.EXTRATO_BANCARIO: BankStatementImporter,
        UploadedFile.FileType.CONTAS_RECEBER: ReceivableImporter,
    }

    importer_cls = importer_map.get(uploaded_file.file_type)
    if importer_cls is None:
        raise ValueError(f"Tipo de arquivo não suportado para importação: '{uploaded_file.file_type}'")

    return importer_cls()
