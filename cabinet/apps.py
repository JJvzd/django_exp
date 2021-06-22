from django.apps import AppConfig


class CabinetConfig(AppConfig):
    name = 'cabinet'
    verbose_name = 'Общее для кабинетов'

    def ready(self):
        import cabinet.signal_handlers  # noqa: F401
