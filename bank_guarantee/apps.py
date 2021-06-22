from django.apps import AppConfig


class BankGuaranteeConfig(AppConfig):
    name = 'bank_guarantee'
    verbose_name = "Банковские гарантии"

    def ready(self):
        import bank_guarantee.bank_integrations.spb_bank.signal_handlers  # noqa: F401
        import bank_guarantee.bank_integrations.moscombank.signal_handlers  # noqa: F401
        import bank_guarantee.signal_handlers  # noqa: F401
        import bank_guarantee.bank_integrations.absolut_bank.signal_handlers  # noqa: F401
        import bank_guarantee.bank_integrations.bks_bank.signal_handlers  # noqa: F401
