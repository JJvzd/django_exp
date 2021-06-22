class ConclusionsGenerator:

    def __init__(self, conclusion_logic):
        self.conclusion_logic = conclusion_logic

    def generate_conclusions(self, base_request, requests_for_send):
        """ Генерация заключек
        :param base_request:
        :param requests_for_send:
        :return:
        """
        banks = list(requests_for_send.values_list('bank__code', flat=True))
        self.conclusion_logic.generate_conclusions(
            client=base_request.client,
            banks_code=banks
        )
