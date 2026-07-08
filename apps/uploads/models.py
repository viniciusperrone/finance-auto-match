import os
import uuid

from django.db import models


def upload_to_path(instance: "UploadedFile", filename: str) -> str:
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex[:8]}_{os.path.splitext(filename)[0]}{ext}"
    subfolder = "extratos" if instance.file_type == UploadedFile.FileType.EXTRATO_BANCARIO else "contas_receber"

    return f"uploads/{subfolder}/{unique_name}"

class UploadedFile(models.Model):
    class FileType(models.TextChoices):
        EXTRATO_BANCARIO = "extrato_bancario", "Extrato Bancário"
        CONTAS_RECEBER = "contas_receber", "Contas a Receber"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente de processamento"
        PROCESSADO = "processado", "Processado"
        ERRO = "erro", "Erro no processamento"

    file_type = models.CharField(
        max_length=32,
        choices=FileType.choices,
        verbose_name="Tipo de arquivo",
    )

    file = models.FileField(upload_to=upload_to_path, verbose_name="Arquivo")
    original_filename = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    processing_notes = models.TextField(blank=True, help_text="Preenchido pelo motor de conciliação")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Arquivo enviado"
        verbose_name_plural = "Arquivos enviados"

    def __str__(self):
        return f"{self.get_file_type_display()} - {self.original_filename or self.file.name}"

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)
        if self.file and not self.size_bytes:
            self.size_bytes = self.file.size

        super().save(*args, **kwargs)
