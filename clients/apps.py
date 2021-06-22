from django.apps import AppConfig


class ClientsConfig(AppConfig):
    name = 'clients'
    verbose_name = 'Компании'

    def ready(self):
        import clients.signal_handlers  # noqa: F401
