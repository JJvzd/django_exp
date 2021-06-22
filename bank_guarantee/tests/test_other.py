from bank_guarantee.models import Offer
from utils.serializaters import generate_serializer


def test_detect_change_model():
    """
    Тест проверяет, что метод определения были ли изменены поля упаковкой в
    сериализатор работает
    """
    offer = Offer(amount=1000)
    serializer = generate_serializer(Offer, ['amount'])
    offer_data = serializer(instance=offer).data
    offer_in_serializer = serializer(data={'amount': offer.amount + 1})
    offer_in_serializer.is_valid()
    new_offer_data = offer_in_serializer.data
    assert offer_data != new_offer_data

    offer_in_serializer = serializer(data={'amount': offer.amount})
    offer_in_serializer.is_valid()
    new_offer_data = offer_in_serializer.data
    assert offer_data == new_offer_data

