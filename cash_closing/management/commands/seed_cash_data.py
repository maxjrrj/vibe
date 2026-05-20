import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from cash_closing.models import DailyClosing, Expense, Store, UserProfile


class Command(BaseCommand):
    help = "Gera dados de fechamento e despesas para múltiplas lojas."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=420, help="Quantidade de dias para gerar")
        parser.add_argument("--clear", action="store_true", help="Apaga fechamentos existentes antes de gerar")

    def handle(self, *args, **options):
        if options["clear"]:
            Expense.objects.all().delete()
            DailyClosing.objects.all().delete()

        stores = [
            Store.objects.get_or_create(code=Store.VILA, defaults={"name": "Vila"})[0],
            Store.objects.get_or_create(code=Store.JACONE, defaults={"name": "Jaconé"})[0],
            Store.objects.get_or_create(code=Store.SAMPAIO, defaults={"name": "Sampaio"})[0],
        ]

        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@vibe.local", "is_staff": True, "is_superuser": True},
        )
        if not admin_user.check_password("admin123"):
            admin_user.set_password("admin123")
            admin_user.save()
        admin_user.profile.role = UserProfile.ADMIN
        admin_user.profile.authorized = True
        admin_user.profile.store = None
        admin_user.profile.save()

        for store in stores:
            username = f"{store.code.lower()}_user"
            user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@vibe.local"})
            if not user.check_password("loja123"):
                user.set_password("loja123")
                user.save()
            user.profile.role = UserProfile.LOJA
            user.profile.authorized = True
            user.profile.store = store
            user.profile.save()

        today = timezone.localdate()
        created = 0
        for offset in range(options["days"]):
            day = today - timedelta(days=offset)
            for store in stores:
                base = Decimal(str(random.uniform(1500, 9000))).quantize(Decimal("0.01"))
                cartao = (base * Decimal(str(random.uniform(0.25, 0.45)))).quantize(Decimal("0.01"))
                pix = (base * Decimal(str(random.uniform(0.15, 0.30)))).quantize(Decimal("0.01"))
                dinheiro = (base - cartao - pix).quantize(Decimal("0.01"))
                deposito = Decimal(str(random.uniform(0, 400))).quantize(Decimal("0.01"))
                cartao_liq = (cartao * Decimal(str(random.uniform(0.95, 0.99)))).quantize(Decimal("0.01"))
                pix_liq = (pix * Decimal(str(random.uniform(0.97, 1.0)))).quantize(Decimal("0.01"))

                closing, was_created = DailyClosing.objects.get_or_create(
                    store=store,
                    closing_date=day,
                    defaults={
                        "dinheiro": dinheiro,
                        "cartao": cartao,
                        "cartao_liquido": cartao_liq,
                        "pix": pix,
                        "pix_liquido": pix_liq,
                        "deposito": deposito,
                    },
                )
                if not was_created:
                    closing.dinheiro = dinheiro
                    closing.cartao = cartao
                    closing.cartao_liquido = cartao_liq
                    closing.pix = pix
                    closing.pix_liquido = pix_liq
                    closing.deposito = deposito
                    closing.save()
                    closing.expenses.all().delete()
                else:
                    created += 1

                for _ in range(random.randint(0, 4)):
                    Expense.objects.create(
                        closing=closing,
                        tipo_despesa=random.choice([c[0] for c in Expense.TIPO_DESPESA_CHOICES]),
                        tipo_pagamento=random.choice([c[0] for c in Expense.TIPO_PAGAMENTO_CHOICES]),
                        valor=Decimal(str(random.uniform(15, 900))).quantize(Decimal("0.01")),
                        descricao=random.choice(
                            [
                                "Reposição de insumos",
                                "Pagamento de serviço",
                                "Manutenção preventiva",
                                "Despesa operacional",
                            ]
                        ),
                    )

                closing.recalculate_totals()
                closing.save(update_fields=["total_bruto", "total_liquido", "total_despesas", "saldo_dia", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Dados gerados para {len(stores)} lojas. Novos fechamentos: {created}"))
