from django.contrib import admin

from .models import DailyClosing, Expense, Store, UserProfile


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "code")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "store", "authorized")
    list_filter = ("role", "authorized", "store")
    search_fields = ("user__username", "user__email")


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0


@admin.register(DailyClosing)
class DailyClosingAdmin(admin.ModelAdmin):
    list_display = ("store", "closing_date", "total_bruto", "total_liquido", "total_despesas", "saldo_dia")
    list_filter = ("store", "closing_date")
    inlines = [ExpenseInline]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("closing", "tipo_despesa", "tipo_pagamento", "valor")
    list_filter = ("tipo_despesa", "tipo_pagamento")
