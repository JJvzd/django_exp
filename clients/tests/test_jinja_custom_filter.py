from cabinet.base_logic.printing_forms.adapters.jinja_custom_filter import Jinja_custom_filter


def test_format_decimal():
    obj = Jinja_custom_filter()
    assert obj.format_decimal(12.1) == '12,10'
    assert obj.format_decimal(9999) == '9 999,00'
    assert obj.format_decimal(0) == '0,00'
    assert obj.format_decimal(-1) == '-1,00'
