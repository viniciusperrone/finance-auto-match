from django.core.management.base import BaseCommand

from apps.reconciliation.services import process_uploaded_file
from apps.uploads.models import UploadedFile


class Command(BaseCommand):
    help = "Processa arquivos pendentes de importação (ou todos, com --all)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action="store_true",
            help="Reprocessa também arquivos já processados ou com erro (substitui os dados existentes)."
        )

        parser.add_argument(
            "--file-id",
            type=int,
            help="Processa apenas o UploadedFile com este id, independente do status."
        )

    def handle(self, *args, **options):
        if options.get("file_id"):
            queryset = UploadedFile.objects.filter(id=options["file_id"])
        elif options["all"]:
            queryset = UploadedFile.objects.all()
        else:
            queryset = UploadedFile.objects.filter(status=UploadedFile.Status.PENDENTE)

        if not queryset.exists():
            self.stdout.write(self.style.WARNING("Nenhum arquivo encontrado para processar."))

            return

        for uploaded_file in queryset:
            result = process_uploaded_file(uploaded_file)
            style = self.style.SUCCESS if result.failed == 0 and result.has_data else self.style.WARNING

            self.stdout.write(
                f"[{uploaded_file.id}] {uploaded_file.original_filename} "
                f"{result.imported} importado(s), {result.failed} erro(s) "
                f"de {result.total_rows} linha(s)."
            )
