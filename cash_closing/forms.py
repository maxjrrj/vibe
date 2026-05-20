from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.forms import inlineformset_factory

from .models import DailyClosing, Expense


class LoginForm(forms.Form):
    username_or_email = forms.CharField(label="Usuário ou e-mail", widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get("username_or_email")
        password = cleaned_data.get("password")

        if not username_or_email or not password:
            return cleaned_data

        user_model = get_user_model()
        username = username_or_email
        if "@" in username_or_email:
            try:
                username = user_model.objects.get(email__iexact=username_or_email).username
            except user_model.DoesNotExist:
                raise forms.ValidationError("Credenciais inválidas.")

        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Credenciais inválidas.")

        cleaned_data["user"] = user
        return cleaned_data


class DailyClosingForm(forms.ModelForm):
    class Meta:
        model = DailyClosing
        fields = ["dinheiro", "cartao", "cartao_liquido", "pix", "pix_liquido", "deposito"]
        widgets = {
            field: forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}) for field in fields
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["tipo_despesa", "tipo_pagamento", "valor", "descricao"]
        widgets = {
            "tipo_despesa": forms.Select(attrs={"class": "form-select"}),
            "tipo_pagamento": forms.Select(attrs={"class": "form-select"}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "descricao": forms.TextInput(attrs={"class": "form-control", "placeholder": "Descrição opcional"}),
        }


ExpenseFormSet = inlineformset_factory(DailyClosing, Expense, form=ExpenseForm, extra=1, can_delete=True)
