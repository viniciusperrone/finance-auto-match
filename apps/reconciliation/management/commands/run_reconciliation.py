from django.core.management.base import BaseCommand

from apps.reconciliation.engine import run_reconciliation


class Command(BaseCommand):
    help = "Executa o motor de conciliação sobre todos os dados atualmente importados."

    def handle(self, *args, **options):
        summary = run_reconciliation()

        self.stdout.write(self.style.SUCCESS("Conciliação executada:"))
        rows = [
            ("Total de contas processadas", summary["total_processado"]),
            ("Conciliado", summary["conciliado"]),
            ("Divergência", summary["divergencia"]),
            ("Pagamento não encontrado", summary["nao_encontrado"]),
            ("Possível pagamento duplicado", summary["possivel_duplicado"]),
        ]
        for label, value in rows:
            self.stdout.write(f"  {label}: {value}")
