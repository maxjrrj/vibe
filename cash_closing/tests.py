from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DailyClosing, Expense, Store, UserProfile


class DailyClosingModelTests(TestCase):
    def setUp(self):
        self.store = Store.objects.create(code=Store.VILA, name="Vila")

    def test_unique_closing_per_store_day(self):
        today = timezone.localdate()
        DailyClosing.objects.create(store=self.store, closing_date=today)
        with self.assertRaises(IntegrityError):
            DailyClosing.objects.create(store=self.store, closing_date=today)

    def test_totals_recalculate_with_expenses(self):
        closing = DailyClosing.objects.create(
            store=self.store,
            closing_date=timezone.localdate() - timedelta(days=1),
            dinheiro=Decimal("100"),
            cartao=Decimal("200"),
            cartao_liquido=Decimal("190"),
            pix=Decimal("50"),
            pix_liquido=Decimal("49"),
            deposito=Decimal("25"),
        )
        Expense.objects.create(closing=closing, tipo_despesa="OUTROS", tipo_pagamento="PIX", valor=Decimal("10"))
        closing.recalculate_totals()

        self.assertEqual(closing.total_bruto, Decimal("375"))
        self.assertEqual(closing.total_liquido, Decimal("364"))
        self.assertEqual(closing.total_despesas, Decimal("10"))
        self.assertEqual(closing.saldo_dia, Decimal("354"))


class AuthorizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.vila = Store.objects.create(code=Store.VILA, name="Vila")
        self.jacone = Store.objects.create(code=Store.JACONE, name="Jaconé")

        self.user = User.objects.create_user(username="loja", password="123456", email="loja@example.com")
        self.user.profile.role = UserProfile.LOJA
        self.user.profile.store = self.vila
        self.user.profile.authorized = True
        self.user.profile.save()

    def test_loja_user_cannot_switch_store(self):
        self.client.login(username="loja", password="123456")
        response = self.client.get(reverse("operational"), {"store": self.jacone.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_store"], self.vila)

    def test_unauthorized_user_blocked(self):
        unauthorized = User.objects.create_user(username="blocked", password="123456")
        unauthorized.profile.authorized = False
        unauthorized.profile.save()

        self.client.login(username="blocked", password="123456")
        response = self.client.get(reverse("operational"))
        self.assertEqual(response.status_code, 403)
