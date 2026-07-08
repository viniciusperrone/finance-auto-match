import os

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_extension(file) -> None:
    ext = os.path.splitext(file.name)[1].lower()
    allowed = settings.UPLOAD_ALLOWED_EXTENSIONS
    if ext not in allowed:
        raise ValidationError(
            f"Extensão '{ext}' não suportada. Extensões aceitas: {', '.join(allowed)}"
        )


def validate_file_size(file) -> None:
    max_size = settings.UPLOAD_MAX_FILE_SIZE

    if file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Arquivo excede o tamanho máximo permitido de {max_mb:.0f}MB."
        )


def validate_upload_file(file) -> None:
    validate_file_extension(file)
    validate_file_size(file)
