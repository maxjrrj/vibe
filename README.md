# Vibe - Fechamento de Caixa (Django)

Aplicação web em Django para fechamento diário de caixa com múltiplas lojas e painel gerencial.

## Requisitos

- Python 3.12+

## Setup local

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_cash_data --days 420
python manage.py createsuperuser  # opcional
python manage.py runserver
```

## Usuários gerados pelo seed

- `admin` / `admin123` (perfil ADMIN, autorizado)
- `vila_user` / `loja123` (perfil LOJA)
- `jacone_user` / `loja123` (perfil LOJA)
- `sampaio_user` / `loja123` (perfil LOJA)

## Funcionalidades principais

- Autenticação por usuário ou e-mail
- Perfis com papéis `ADMIN` e `LOJA`
- Restrição de acesso por autorização explícita no perfil
- Uma única abertura de fechamento por loja por dia (restrição de banco)
- Edição permitida somente para o dia atual no fluxo operacional
- Despesas opcionais com múltiplas linhas e exclusão antes do salvamento final
- Persistência de totais calculados (`total_bruto`, `total_liquido`, `total_despesas`, `saldo_dia`)
- Dashboard gerencial separado com gráficos em Chart.js
- Modelos registrados no Django Admin

## URLs

- `/login/` — autenticação
- `/operacional/` — fechamento diário
- `/dashboard/` — painel gerencial (somente ADMIN)
- `/admin/` — administração Django
