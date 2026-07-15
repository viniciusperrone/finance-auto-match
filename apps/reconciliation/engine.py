import difflib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from decimal import Decimal

from django.conf import settings
from django.db import transaction


from apps.reconciliation.models import BankTransaction, Receivable, ReconciliationResult

DATE_WINDOW_BEFORE_DAYS = getattr(settings, "RECONCILIATION_DATE_WINDOW_BEFORE_DAYS", 5)
DATE_WINDOW_AFTER_DAYS = getattr(settings, "RECONCILIATION_DATE_WINDOW_AFTER_DAYS", 10)
AMOUNT_TOLERANCE_RATIO = getattr(settings, "RECONCILIATION_AMOUNT_TOLERANCE_RATIO", Decimal("0.05"))
WEIGHT_AMOUNT = getattr(settings, "RECONCILIATION_WEIGHT_AMOUNT", 0.5)
WEIGHT_DATE = getattr(settings, "RECONCILIATION_WEIGHT_DATE", 0.25)
WEIGHT_DESCRIPTION = getattr(settings, "RECONCILIATION_WEIGHT_DESCRIPTION", 0.25)
CONCILIADO_MIN_SCORE = getattr(settings, "RECONCILIATION_CONCILIADO_MIN_SCORE", 60)
EXACT_AMOUNT_TOLERANCE = Decimal("0.01")

MAX_CANDIDATES_STORED = 5


@dataclass
class MatchCandidate:
    bank_transaction: BankTransaction
    score: float
    amount_score: float
    date_score: float
    description_score: float
    amount_difference: Decimal
    date_difference_days: int

    def as_dict(self) -> dict:
        return {
            "bank_transaction_id": self.bank_transaction.id,
            "score": round(self.score, 2),
            "amount": str(self.bank_transaction.amount),
            "date": self.bank_transaction.transaction_date.isoformat(),
            "description": self.bank_transaction.description,
            "amount_difference": str(self.amount_difference),
            "date_difference_days": self.date_difference_days,
        }

@dataclass
class ReconciliationOutcome:
    receivable: Receivable
    status: str
    score: Decimal
    best_candidate: Optional[MatchCandidate]
    candidates: list
    notes: str

def _amount_score(expected: Decimal, actual: Decimal) -> float:
    if expected == 0:
        return 1.0 if actual == 0 else 0.0

    diff_ratio = abs(actual - expected) / expected
    if diff_ratio >= AMOUNT_TOLERANCE_RATIO:
        return 0.0

    return float(1 - (diff_ratio / AMOUNT_TOLERANCE_RATIO))

def _date_score(due_date: date, transaction_date: date) -> float:
    delta_days = (transaction_date - due_date).days
    window = DATE_WINDOW_AFTER_DAYS if delta_days >= 0 else DATE_WINDOW_BEFORE_DAYS
    delta_abs = abs(delta_days)

    if window == 0:
        return 1.0 if delta_abs == 0 else 0.0
    if delta_abs > window:
        return 0.0

    return float(1 - (delta_abs / window))

def _description_score(client_name_normalized: str, description_normalized: str) -> float:
    if not client_name_normalized or not description_normalized:
        return 0.0

    ratio = difflib.SequenceMatcher(None, client_name_normalized, description_normalized).ratio()
    tokens = [t for t in client_name_normalized.split(" ") if t]

    if tokens and all(token in description_normalized for token in tokens):
        ratio = max(ratio, 0.9)

    return ratio

def find_candidates(receivable: Receivable, bank_transactions) -> list:
    candidates = []
    for transaction_ in bank_transactions:
        date_score = _date_score(receivable.due_date, transaction_.transaction_date)
        if date_score == 0.0:
            continue

        amount_score = _amount_score(receivable.expected_amount, transaction_.amount)
        if amount_score == 0.0:
            continue

        description_score = _description_score(
            receivable.client_name_normalized,
            transaction_.description_normalized
        )

        score = 100 * (
            WEIGHT_AMOUNT * amount_score + WEIGHT_DATE * date_score + WEIGHT_DESCRIPTION * description_score
        )

        candidates.append(MatchCandidate(
            bank_transaction=transaction_,
            score=score,
            amount_score=amount_score,
            date_score=date_score,
            description_score=description_score,
            amount_difference=(transaction_.amount - receivable.expected_amount),
            date_difference_days=(transaction_.transaction_date - receivable.due_date).days,

        ))

    candidates.sort(key=lambda c: c.score, reverse=True)

    return candidates

def classify(receivable: Receivable, candidates: list) -> ReconciliationOutcome:
    if not candidates:
        return ReconciliationOutcome(
            receivable=receivable,
            status=ReconciliationResult.Status.NAO_ENCONTRADO,
            score=Decimal("0.00"),
            best_candidate=None,
            candidates=[],
            notes=(
                "Nenhuma transação compatível encontrada dentro da janela de data "
                f"(-{DATE_WINDOW_BEFORE_DAYS}/+{DATE_WINDOW_AFTER_DAYS} dias do vencimento) "
                f"e tolerância de valor ({AMOUNT_TOLERANCE_RATIO:.0%})."
            )
        )
    exact_matches = [c for c in candidates if abs(c.amount_difference) <= EXACT_AMOUNT_TOLERANCE]
    best = candidates[0]

    if len(exact_matches) >= 2:
        details = "; ".join(
            f"{c.bank_transaction.transaction_date.strftime('%d/%m/%Y')}{ ({c.bank_transaction.description})}"
            for c in exact_matches[:MAX_CANDIDATES_STORED]
        )

        return ReconciliationOutcome(
            receivable=receivable,
            status=ReconciliationResult.Status.POSSIVEL_DUPLICADO,
            score=Decimal(str(round(best.score, 2))),
            best_candidate=best,
            candidates=candidates,
            notes=(
                f"Mais de uma transação bate exatamente com o valor esperado "
                f"(R$ {receivable.expected_amount}): {details}. Verifique se não houve pagamento em duplicidade."
            )
        )

    exact_amount = abs(best.amount_difference) <= EXACT_AMOUNT_TOLERANCE
    if exact_amount and best.score >= CONCILIADO_MIN_SCORE:
        status = ReconciliationResult.Status.CONCILIADO
        notes = (
            f"Conciliado com a transação de {best.bank_transaction.transaction_date.strftime('%d/%m/%Y')} "
            f"({best.bank_transaction.description})."
        )
    else:
        status = ReconciliationResult.Status.DIVERGENCIA
        sinal = "a mais" if best.amount_difference > 0 else "a menos"
        notes = (
            f"Melhor correspondência em {best.bank_transaction.transaction_date.strftime('%d/%m/%Y')} "
            f"({best.bank_transaction.description}), mas o valor está R$ {abs(best.amount_difference)} {sinal} "
            f"em relação ao esperado (score {best.score:.0f}/100)."
        )

    return ReconciliationOutcome(
        receivable=receivable,
        status=status,
        score=Decimal(str(round(best.score, 2))),
        best_candidate=best,
        candidates=candidates,
        notes=notes,
    )

def _flag_cross_receivable_duplicates(outcomes: list) -> None:
    usage_by_transaction = defaultdict(list)
    for outcome in outcomes:
        if outcome.best_candidate is not None:
            usage_by_transaction[outcome.best_candidate.bank_transaction.id].append(outcome)

    for transaction_id, group in usage_by_transaction.items():
        if len(group) < 2:
            continue

        client_names = ", ".join(o.receivable.client_name for o in group)
        transaction_ = group[0].best_candidate.bank_transaction

        for outcome in group:
            outcome.status = ReconciliationResult.Status.POSSIVEL_DUPLICADO
            outcome.notes = (
                f"A transação de {transaction_.transaction_date.strftime('%d/%m/%Y')} "
                f"({transaction_.description}) também é a melhor correspondência para: {client_names}. "
                "Verifique manualmente qual conta ela realmente quita."
            )

def _outcome_to_model(outcome: ReconciliationOutcome) -> ReconciliationResult:
    best = outcome.best_candidate

    return ReconciliationResult(
        receivable=outcome.receivable,
        bank_transaction=best.bank_transaction if best else None,
        status=outcome.status,
        score=outcome.score,
        amount_difference=best.amount_difference if best else None,
        date_difference_days=best.date_difference_days if best else None,
        notes=outcome.notes,
        candidates_considered=[c.as_dict() for c in outcome.candidates[:MAX_CANDIDATES_STORED]],
    )

def _summarize(outcomes: list) -> dict:
    counts = Counter(o.status for o in outcomes)
    return {
        "total_processado": len(outcomes),
        "conciliado": counts.get(ReconciliationResult.Status.CONCILIADO, 0),
        "divergencia": counts.get(ReconciliationResult.Status.DIVERGENCIA, 0),
        "nao_encontrado": counts.get(ReconciliationResult.Status.NAO_ENCONTRADO, 0),
        "possivel_duplicado": counts.get(ReconciliationResult.Status.POSSIVEL_DUPLICADO, 0),
    }

def run_reconciliation() -> dict:
    receivables = list(Receivable.objects.all())
    bank_transactions = list(BankTransaction.objects.all())

    outcomes = []
    for receivable in receivables:
        candidates = find_candidates(receivable, bank_transactions)
        outcomes.append(classify(receivable, candidates))

    _flag_cross_receivable_duplicates(outcomes)

    with transaction.atomic():
        ReconciliationResult.objects.all().delete()
        if outcomes:
            ReconciliationResult.objects.bulk_create([_outcome_to_model(o) for o in outcomes])

    return _summarize(outcomes)
