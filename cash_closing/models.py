from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Store(models.Model):
    VILA = "VILA"
    JACONE = "JACONE"
    SAMPAIO = "SAMPAIO"

    STORE_CHOICES = [
        (VILA, "Vila"),
        (JACONE, "Jaconé"),
        (SAMPAIO, "Sampaio"),
    ]

    code = models.CharField(max_length=20, unique=True, choices=STORE_CHOICES)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ADMIN = "ADMIN"
    LOJA = "LOJA"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (LOJA, "Loja"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=LOJA)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL, related_name="users")
    authorized = models.BooleanField(default=False)

    def clean(self):
        if self.role == self.LOJA and not self.store:
            raise ValidationError("Usuários LOJA precisam de uma loja atribuída.")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class DailyClosing(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="closings")
    closing_date = models.DateField()

    dinheiro = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cartao = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cartao_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pix = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pix_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposito = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_bruto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_liquido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_despesas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_dia = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["store", "closing_date"], name="unique_store_closing_day")]
        ordering = ["-closing_date", "store__name"]

    def __str__(self):
        return f"{self.store.name} - {self.closing_date:%d/%m/%Y}"

    def recalculate_totals(self):
        self.total_bruto = self.dinheiro + self.cartao + self.pix + self.deposito
        self.total_liquido = self.dinheiro + self.cartao_liquido + self.pix_liquido + self.deposito
        expense_total = self.expenses.aggregate(total=models.Sum("valor"))["total"]
        self.total_despesas = expense_total or Decimal("0")
        self.saldo_dia = self.total_liquido - self.total_despesas

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Expense(models.Model):
    TIPO_DESPESA_CHOICES = [
        ("ALUGUEL", "Aluguel"),
        ("FORNECEDOR", "Fornecedor"),
        ("MANUTENCAO", "Manutenção"),
        ("SALARIO", "Salário"),
        ("OUTROS", "Outros"),
    ]
    TIPO_PAGAMENTO_CHOICES = [
        ("DINHEIRO", "Dinheiro"),
        ("PIX", "PIX"),
        ("CARTAO", "Cartão"),
        ("TRANSFERENCIA", "Transferência"),
    ]

    closing = models.ForeignKey(DailyClosing, on_delete=models.CASCADE, related_name="expenses")
    tipo_despesa = models.CharField(max_length=30, choices=TIPO_DESPESA_CHOICES)
    tipo_pagamento = models.CharField(max_length=30, choices=TIPO_PAGAMENTO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.tipo_despesa} - R$ {self.valor}"
