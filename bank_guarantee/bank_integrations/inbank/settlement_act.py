from settlement_acts.adapters import BaseExcel


class Inbank(BaseExcel):
    template = 'inbank'

    def fill_table(self, start, data=None):
        if data is None:
            data = {}

        row = start
        for i, request in enumerate(self.data['requests']):
            row = start + i
            data.update({
                'A%i' % row: i + 1,
                'B%i' % row: request.client.profile.short_name,
                'C%i' % row: request.offer.contract_number,
                'D%i' % row: request.offer.contract_date.strftime('%d.%m.%Y'),
                'E%i' % row: 'БГ',
                'F%i' % row: request.offer.amount,
                'G%i' % row: request.offer.commission_bank,
                'H%i' % row: request.offer.delta_commission_bank,
                'I%i' % row: request.offer.commission_bank,
            })
        self.add_insert_rows(start, len(self.data['requests']) - 1)
        return data, row

    def get_data(self):
        data = {
            'D2': "АКТ–ОТЧЕТ №\nпо заключенным при посредничестве Агента\n"
                  "договорам о предоставлении Банковских продуктов\n"
                  "за период %s %i г. " % (self.data['month'], self.data['year'])
        }
        start = 10
        data, end = self.fill_table(start, data=data)
        data.update({
            'F%i' % (end + 1): '=SUM(F%i:F%i)' % (start, end),
            'M%i' % (end + 1): '=SUM(M%i:M%i)' % (start, end),
        })

        return [[*self.parse_row_and_col(k), v] for k, v in data.items()]
