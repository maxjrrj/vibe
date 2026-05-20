import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import ExtractDay, ExtractWeekDay, TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DailyClosingForm, ExpenseFormSet, LoginForm
from .models import DailyClosing, Expense, Store, UserProfile

WEEKDAY_LABELS = {
    1: "Domingo",
    2: "Segunda",
    3: "Terça",
    4: "Quarta",
    5: "Quinta",
    6: "Sexta",
    7: "Sábado",
}


def home_redirect(request):
    return redirect("operational" if request.user.is_authenticated else "login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("operational")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        return redirect("operational")

    return render(request, "cash_closing/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


def _get_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist as exc:
        raise PermissionDenied("Usuário sem perfil configurado.") from exc


def _deny_if_unauthorized(profile):
    if not profile.authorized:
        return HttpResponseForbidden("Usuário não autorizado.")
    return None


def _resolve_store(request, profile):
    stores = Store.objects.all()
    if not stores.exists():
        raise PermissionDenied("Nenhuma loja configurada.")

    if profile.role == UserProfile.LOJA:
        if not profile.store:
            raise PermissionDenied("Usuário LOJA sem loja atribuída.")
        return profile.store, stores

    selected_id = request.GET.get("store") if request.method == "GET" else request.POST.get("store")
    if selected_id:
        return get_object_or_404(Store, pk=selected_id), stores
    return stores.first(), stores


@login_required
@transaction.atomic
def operational_view(request):
    profile = _get_profile(request.user)
    unauthorized = _deny_if_unauthorized(profile)
    if unauthorized:
        return unauthorized

    selected_store, all_stores = _resolve_store(request, profile)
    today = timezone.localdate()
    closing = DailyClosing.objects.filter(store=selected_store, closing_date=today).first()

    wants_edit = request.GET.get("edit") == "1"
    blocked = request.method == "GET" and closing is not None and not wants_edit

    if request.method == "POST":
        closing_instance = closing or DailyClosing(store=selected_store, closing_date=today)
        form = DailyClosingForm(request.POST, instance=closing_instance)
        formset = ExpenseFormSet(request.POST, instance=closing_instance, prefix="expenses")

        if form.is_valid() and formset.is_valid():
            closing_obj = form.save(commit=False)
            closing_obj.store = selected_store
            closing_obj.closing_date = today
            closing_obj.save()
            formset.instance = closing_obj
            formset.save()
            closing_obj.recalculate_totals()
            closing_obj.save(update_fields=["total_bruto", "total_liquido", "total_despesas", "saldo_dia", "updated_at"])
            messages.success(request, "Fechamento salvo com sucesso.")
            return redirect(f"/operacional/?store={selected_store.id}&edit=1")
    else:
        form = DailyClosingForm(instance=closing)
        formset = ExpenseFormSet(instance=closing or DailyClosing(store=selected_store, closing_date=today), prefix="expenses")

    return render(
        request,
        "cash_closing/operational.html",
        {
            "profile": profile,
            "stores": all_stores,
            "selected_store": selected_store,
            "today": today,
            "closing": closing,
            "blocked": blocked,
            "form": form,
            "formset": formset,
            "is_admin": profile.role == UserProfile.ADMIN,
        },
    )


@login_required
def dashboard_view(request):
    profile = _get_profile(request.user)
    unauthorized = _deny_if_unauthorized(profile)
    if unauthorized:
        return unauthorized
    if profile.role != UserProfile.ADMIN:
        raise PermissionDenied("Apenas admins podem acessar o dashboard.")

    closings = DailyClosing.objects.all()
    highest_day = closings.order_by("-total_bruto").select_related("store").first()

    by_day_of_month = list(
        closings.annotate(day=ExtractDay("closing_date")).values("day").annotate(total=Sum("total_bruto")).order_by("day")
    )
    by_weekday = list(
        closings.annotate(day=ExtractWeekDay("closing_date")).values("day").annotate(total=Sum("total_bruto")).order_by("day")
    )

    expenses_by_month = list(
        Expense.objects.annotate(month=TruncMonth("closing__closing_date"))
        .values("month")
        .annotate(total=Sum("valor"))
        .order_by("month")
    )

    def segmented_growth(field_name):
        grouped = list(
            Expense.objects.annotate(month=TruncMonth("closing__closing_date"))
            .values("month", field_name)
            .annotate(total=Sum("valor"))
            .order_by("month")
        )
        months = sorted({row["month"] for row in grouped if row["month"]})
        categories = sorted({row[field_name] for row in grouped if row[field_name]})
        month_labels = [month.strftime("%m/%Y") for month in months]
        month_index = {month: idx for idx, month in enumerate(months)}

        datasets = []
        for category in categories:
            values = [0.0] * len(months)
            for row in grouped:
                if row[field_name] == category and row["month"] in month_index:
                    values[month_index[row["month"]]] = float(row["total"] or 0)
            datasets.append({"label": category, "data": values})
        return {"labels": month_labels, "datasets": datasets}

    best_day_month = max(by_day_of_month, key=lambda row: row["total"], default=None)
    worst_day_month = min(by_day_of_month, key=lambda row: row["total"], default=None)
    best_weekday = max(by_weekday, key=lambda row: row["total"], default=None)
    worst_weekday = min(by_weekday, key=lambda row: row["total"], default=None)

    context = {
        "highest_day": highest_day,
        "day_of_month_chart": json.dumps(
            {"labels": [str(row["day"]) for row in by_day_of_month], "values": [float(row["total"] or 0) for row in by_day_of_month]}
        ),
        "weekday_chart": json.dumps(
            {
                "labels": [WEEKDAY_LABELS[row["day"]] for row in by_weekday],
                "values": [float(row["total"] or 0) for row in by_weekday],
            }
        ),
        "expense_month_chart": json.dumps(
            {
                "labels": [row["month"].strftime("%m/%Y") for row in expenses_by_month if row["month"]],
                "values": [float(row["total"] or 0) for row in expenses_by_month if row["month"]],
            }
        ),
        "expense_by_type_chart": json.dumps(segmented_growth("tipo_despesa")),
        "expense_by_payment_chart": json.dumps(segmented_growth("tipo_pagamento")),
        "best_day_month": best_day_month,
        "worst_day_month": worst_day_month,
        "best_weekday": best_weekday,
        "worst_weekday": worst_weekday,
        "best_weekday_label": WEEKDAY_LABELS.get(best_weekday["day"]) if best_weekday else None,
        "worst_weekday_label": WEEKDAY_LABELS.get(worst_weekday["day"]) if worst_weekday else None,
    }
    return render(request, "cash_closing/dashboard.html", context)
