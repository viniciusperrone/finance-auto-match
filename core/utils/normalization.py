import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

def normalize_column_name(name: str) -> str:
    name = strip_accents(str(name)).strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)

    return name

def normalize_text(value) -> str:
    if value is None:
        return ""

    text = strip_accents(str(value)).strip().upper()
    text = re.sub(r"\s+", "_", text)

    return text

def normalize_amount(value) -> Decimal:
    if value is None:
        raise ValueError("Valor monetário vazio")

    if isinstance(value, float) and value != value:
        raise ValueError("Valor monetário vazio")

    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))

    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(Decimal("0.01"))

    text = str(value).strip()
    if not text:
        raise ValueError("Valor monetário vazio")

    text = re.sub(r"[^\d,.\-]", "", text)
    if not text:
        raise ValueError(f"Valor monetário inválido: '{value}'")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".") if text.count(",") == 1 else text.replace(",", "")

    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: '{value}'") from exc

def normalize_date(value) -> date:
    if value is None:
        raise ValueError("Data vazia")

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text.lower() == "nat":
        raise ValueError("Data vazia")

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Data inválida: '{value}'")
