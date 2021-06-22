import django.dispatch


# вызывается, когда заявка оказалась в банке и видна ему для одобрения или отказа
request_sent_in_bank = django.dispatch.Signal(providing_args=['request', 'wait_sign'])

# вызывается, когда выполнился action создания предложения
request_create_offer = django.dispatch.Signal(providing_args=['request'])

# клиент принял предложение
client_confirm_offer = django.dispatch.Signal(providing_args=['request'])

# БГ выдана
finish_request = django.dispatch.Signal(providing_args=['request'])

# Получен ответ на дозапрос
get_ask_on_query = django.dispatch.Signal(providing_args=['request', 'user'])

# Заявка приняла оплату
request_confirm_pay = django.dispatch.Signal(providing_args=['request'])
