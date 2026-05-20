from django.apps import AppConfig


class CashClosingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cash_closing"

    def ready(self):
        import cash_closing.signals  # noqa: F401
