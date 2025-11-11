from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"

    def ready(self) -> None:  # pragma: no cover - import side effects
        super().ready()
        # Import signal handlers to keep admin overview caches fresh.
        from . import signals  # noqa: F401
        try:
            from .views import trigger_overview_warmup_async

            trigger_overview_warmup_async(force=True)
        except Exception:
            # Startup warmup is best-effort; failures are logged by the helper.
            pass
