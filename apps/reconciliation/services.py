from apps.uploads.models import UploadedFile

from .importers import ImportResult, get_importer_for
from apps.reconciliation.engine import run_reconciliation


def process_uploaded_file(uploaded_file: UploadedFile) -> ImportResult:
    try:
        importer = get_importer_for(uploaded_file)
        result = importer.import_file(uploaded_file)
    except Exception as exc:
        uploaded_file.status = UploadedFile.Status.ERRO
        uploaded_file.processing_notes = f"Falha ao importar arquivo: {exc}"
        uploaded_file.save(update_fields=["status", "processing_notes"])

        return ImportResult(errors=[{"row": None, "message": str(exc)}])

    if not result.has_data:
        uploaded_file.status = UploadedFile.Status.ERRO
        uploaded_file.processing_notes = "Arquivo vazio ou sem limites de dados."
    elif result.imported == 0:
        uploaded_file.status = UploadedFile.Status.ERRO
        uploaded_file.processing_notes = f"Nenhum registro importado. {result.failed} linhas(s) com error."
    else:
        uploaded_file.status = UploadedFile.Status.PROCESSADO
        if result.failed == 0:
            uploaded_file.processing_notes = f"{result.imported} registro(s) importado(s) com sucesso."
        else:
            uploaded_file.processing_notes = (
                f"{result.imported} registro(s) importado(s), {result.failed} linha(s) com erro "
                "(ver detalhes em Problemas de importação no admin)."
            )

        try:
            run_reconciliation()
        except Exception as exc:
            uploaded_file.processing_notes += f" [Aviso: falha ao recalcular a conciliação: {exc}]"

    uploaded_file.save(update_fields=["status", "processing_notes"])

    return result
