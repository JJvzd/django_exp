import datetime
import traceback
import decimal

from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from bank_guarantee.constants import ProductChoices
from bank_guarantee.models import Request, Offer, RequestHistory
from cabinet.api.viewsets.requests_common import RequestsViewSet
from cabinet.base_logic.reports.generate.export_requests import ExportRequests
from cabinet.base_logic.reports.generate.funnel_report import SalesFunnelReport
from cabinet.base_logic.reports.generate.sales_report import SalesReport
from cabinet.base_logic.reports.generate.request_report import RequestReport
from cabinet.base_logic.reports.generate.manager_request_report import (
    ManagerRequestReport
)
from cabinet.base_logic.reports.generate.month_dynamics_request_report import (
    MonthDynamicsRequestReport
)
from cabinet.base_logic.reports.generate.bank_request_report import (
    BankRequestReport
)
from cabinet.base_logic.reports.generate.structure_report import (
    StructureRequestReport
)
from cabinet.base_logic.reports.generate.load_on_manager import LoadOnManagerReport
from cabinet.base_logic.reports.generate.manager_plan_executing import (
    ManagerPlanExecutingReport
)
from cabinet.base_logic.reports.generate.operation_manager_report import (
    OperationManagerReport
)
from clients.models import Agent, AgentContractOffer, AgentManager, Client, Bank
from clients.serializers import AgentSerializerForSelectInput
from permissions.logic.bank_guarantee import GetUserAllowedRequests
from permissions.logic.tender_loans import GetUserAllowedLoanRequests
from tender_loans.models import LoanRequest
from users.models import Role, User
from users.serializers import UserForSelectInput

from django.db.models import Sum
from django.db.models.functions import Coalesce
from cabinet.base_logic.reports.generate.base import BaseReport, BaseReportResult


class ReportViewSet(viewsets.ViewSet):

    @drf_action(detail=False, methods=['GET'])
    def get_manager_plan_executing(self, request):
        errors = []
        if not request.query_params.get('date_from'):
            errors.append('Заполните поле "Период с"')
        if not request.query_params.get('date_to'):
            errors.append('Заполните поле "Период по"')
        if not request.query_params.get('product'):
            errors.append('Заполните поле "Тип продукта"')
        if not request.query_params.get('manager'):
            errors.append('Заполните поле "Менеджер"')

        if errors:
            return Response({
                'errors': errors
            })
        date_from = request.query_params.get('date_from').split('-')
        date_from = datetime.datetime(*[int(i) for i in date_from])

        date_to = request.query_params.get('date_to').split('-')
        date_to = datetime.datetime(*[int(i) for i in date_to])

        product = request.query_params.get('product')
        manager = request.query_params.get('manager')
        report_dict = ManagerPlanExecutingReport(
            date_from, date_to, product, manager
        ).generate()
        return Response({
            'report': report_dict.file_path,
            'name': report_dict.output_name,
        })

    @drf_action(detail=False, methods=['GET'])
    def get_operation_manager_report(self, request):
        errors = []
        if not request.query_params.get('date_from'):
            errors.append('Заполните поле "Период с"')
        if not request.query_params.get('date_to'):
            errors.append('Заполните поле "Период по"')
        if not request.query_params.get('product'):
            errors.append('Заполните поле "Тип продукта"')
        if not request.query_params.get('manager'):
            errors.append('Заполните поле "Менеджер"')
        if not request.query_params.get('agent'):
            errors.append('Заполните поле "Агент"')
        if errors:
            return Response({
                'errors': errors
            })
        date_from = request.query_params.get('date_from').split('-')
        date_from = datetime.datetime(*[int(i) for i in date_from])

        date_to = request.query_params.get('date_to').split('-')
        date_to = datetime.datetime(*[int(i) for i in date_to])
        product = request.query_params.get('product')
        manager = request.query_params.get('manager')
        agent = request.query_params.get('agent')
        report_dict = OperationManagerReport(
            date_from, date_to, product, manager, agent
        ).generate()
        return Response({
            'report': report_dict.file_path,
            'name': report_dict.output_name,
        })

    @drf_action(detail=False, methods=['GET'])
    def get_load_on_manager(self, request):
        errors = []
        if not request.query_params.get('date_from'):
            errors.append('Заполните поле "Период с"')
        if not request.query_params.get('date_to'):
            errors.append('Заполните поле "Период по"')
        if not request.query_params.get('product'):
            errors.append('Заполните поле "Тип продукта"')
        if not request.query_params.get('manager'):
            errors.append('Заполните поле "Менеджер"')
        if not request.query_params.get('agent'):
            errors.append('Заполните поле "Агент"')
        if errors:
            return Response({
                'errors': errors
            })
        date_from = request.query_params.get('date_from').split('-')
        date_from = datetime.datetime(*[int(i) for i in date_from])

        date_to = request.query_params.get('date_to').split('-')
        date_to = datetime.datetime(*[int(i) for i in date_to])

        product = request.query_params.get('product')
        manager = request.query_params.get('manager')
        agent = request.query_params.get('agent')
        report_dict = LoadOnManagerReport(
            date_from, date_to, product, manager, agent
        ).generate()

        return Response({
            'report': report_dict.file_path,
            'name': report_dict.output_name,
        })

    @drf_action(detail=False, methods=['GET'])
    def export_requests(self, request):
        requests = Request.objects.all()
        requests = GetUserAllowedRequests().execute(
            self.request.user, requests=requests
        ).select_related()
        loans = LoanRequest.objects.all()
        loans = GetUserAllowedLoanRequests().execute(
            self.request.user, requests=loans
        ).select_related()
        archive = self.request.query_params.get('archive') == 'true'
        if requests:
            requests = RequestsViewSet.filter_queryset(
                self.request.query_params, requests.filter(in_archive=archive)
            )
        else:
            requests = None

        if loans:
            loans = RequestsViewSet.filter_queryset(
                self.request.query_params, requests.filter(in_archive=archive)
            )
        else:
            loans = None
        export_requests = ExportRequests(
            requests=requests,
            loans=loans.filter(in_archive=archive) if loans else None,
            role=request.user.roles_list
        )
        if request.query_params.get('extension') == 'pdf':
            report_result = export_requests.generate_pdf()
        else:
            report_result = export_requests.generate()
        return Response({
            'report': report_result.file_path,
            'name': report_result.output_name,
        })

    @drf_action(detail=False, methods=['POST', 'GET'])
    def generate_request_report(self, *args, **kwargs):
        from request_parser.views import RequestParserViewSet
        from datetime import datetime as dt
        date_from = self.request.data.get('date_from')
        date_to = self.request.data.get('date_to')

        s, e = list(map(lambda x: int(dt.strptime(x, '%Y-%m-%d').timestamp()), \
                        [date_from, date_to]
                        ))
        list_of_dates = \
            [dt.fromtimestamp(x).strftime('%Y-%m-%d') for x in range(s, e + 86400, 86400)]

        result_list = dict()
        result_list["requests"] = list()
        row_number = 1

        for date in list_of_dates:
            request_data = RequestParserViewSet.generate_request_report(self, date)
            row_number += 1
            request_data["row_number"] = row_number
            result_list["requests"] += \
                RequestReport(request_data=request_data).get_data()["requests"]

        if request_data is None:
            return Response({
                'errors': "error"
            })

        br_object = BaseReport()
        br_object.template_name = 'system_files/report_templates/request_report.xlsx'

        result = BaseReportResult(
            file_path=br_object.write_to_file(data=result_list),
            output_name=br_object.get_output_filename()
        )

        return Response({
            'report': result.file_path,
            'name': result.output_name,
        })

    @drf_action(detail=False, methods=['POST', 'GET'])
    def generate_sales_report(self, *args, **kwargs):
        date = self.request.data.get('date')
        try:
            result = SalesReport(
                date=date
            ).generate()
        except Exception:
            return Response({'error': traceback.format_exc(10)})

        return Response({
            'report': result.file_path,
            'name': result.output_name,
        })

    @drf_action(detail=False, methods=['POST'])
    def requests_funnel(self, *args, **kwargs):
        try:
            result = SalesFunnelReport(
                from_month=self.request.data.get('from_month'),
                from_year=self.request.data.get('from_year'),
            ).generate()
        except Exception:
            return Response({'error': traceback.format_exc(10)})
        return Response({
            'report': result.file_path,
            'name': result.output_name,
        })

    def get_bg_and_comission_sum(self, request_model):
        bg_sum = 0
        comission_sum = 0
        offer_requests = Offer.objects.filter(
            request_id__in=request_model.values_list('id', flat=True)
        )

        for request in offer_requests:
            bg_sum += request.amount
            comission_sum += request.commission_bank

        return bg_sum, comission_sum

    def get_overall_result(self, bank_data):
        overall_result = dict()
        overall_result["all_requests"] = 0
        overall_result["requests_done"] = 0
        overall_result["unreached_requests"] = 0
        overall_result["avg_bg_sum"] = 0
        overall_result["commission_requests"] = 0
        overall_result["conversion"] = 0
        overall_result["verification_requests"] = 0
        overall_result["issued"] = 0
        overall_result["avg_bg_sum_issued_request"] = 0
        overall_result["comissoion_issued"] = 0
        overall_result["conversion_issued_to_exhibited"] = 0
        overall_result["conversion_issued_to_exhibited_by_value"] = 0
        overall_result["conversion_issued_to_all"] = 0

        for bank_id, bank_value in bank_data.items():
            overall_result["all_requests"] += bank_value["all_requests"].count()
            overall_result["requests_done"] += bank_value["requests_done"].count()
            overall_result["unreached_requests"] += (
                bank_value["unreached_requests"].count()
                if bank_value["unreached_requests"].count() is not None else 0)
            overall_result["avg_bg_sum"] += (
                decimal.Decimal(bank_value["avg_bg_sum"])
                if bank_value["avg_bg_sum"] is not None else 0)
            overall_result["commission_requests"] += (
                decimal.Decimal(bank_value["commission_requests"])
                if bank_value["commission_requests"] is not None else 0)
            overall_result["conversion"] += (
                decimal.Decimal(bank_value["conversion"])
                if bank_value["conversion"] is not None else 0)
            overall_result["verification_requests"] += (
                decimal.Decimal(bank_value["verification_requests"])
                if bank_value["verification_requests"] is not None else 0)
            overall_result["issued"] += bank_value["issued"].count()
            overall_result["avg_bg_sum_issued_request"] += (
                decimal.Decimal(bank_value["avg_bg_sum_issued_request"])
                if bank_value["avg_bg_sum_issued_request"] is not None else 0)
            overall_result["comissoion_issued"] += (
                decimal.Decimal(bank_value["comissoion_issued"])
                if bank_value["comissoion_issued"] is not None else 0)
            overall_result["conversion_issued_to_exhibited"] += (
                decimal.Decimal(bank_value["conversion_issued_to_exhibited"])
                if bank_value["conversion_issued_to_exhibited"] is not None else 0)
            overall_result["conversion_issued_to_exhibited_by_value"] += (
                decimal.Decimal(bank_value["conversion_issued_to_exhibited_by_value"])
                if (bank_value["conversion_issued_to_exhibited_by_value"]
                    is not None) else 0)
            overall_result["conversion_issued_to_all"] += (
                decimal.Decimal(bank_value["conversion_issued_to_all"])
                if bank_value["conversion_issued_to_all"] is not None else 0)
        return overall_result

    def get_bank_data(self, all_requests, requests_done,
                      unreached_requests, directed_requests,
                      issued_requests, offer_requests, accepted_requests,
                      revoked_client_requests, for_issue_requests):
        directed_bg_sum, directed_comission_sum = (
            self.get_bg_and_comission_sum(directed_requests))
        issued_bg_sum, issued_comission_sum = (
            self.get_bg_and_comission_sum(issued_requests))
        offer_bg_sum, offer_comission_sum = (
            self.get_bg_and_comission_sum(offer_requests))
        accepted_bg_sum, accepted_comission_sum = (
            self.get_bg_and_comission_sum(accepted_requests))
        revoked_client_bg_sum, revoked_client_comission_sum = (
            self.get_bg_and_comission_sum(revoked_client_requests))
        for_issued_bg_sum, for_issued_comission_sum = (
            self.get_bg_and_comission_sum(for_issue_requests))

        # Средняя сумма БГ
        try:
            avg_bg_sum = (offer_bg_sum +
                          issued_bg_sum +
                          accepted_bg_sum +
                          revoked_client_bg_sum +
                          for_issued_bg_sum
                          ) / (directed_requests.count() +
                               issued_requests.count() +
                               offer_requests.count() +
                               accepted_requests.count() +
                               revoked_client_requests.count() +
                               for_issue_requests.count()
                               )
        except ZeroDivisionError:
            avg_bg_sum = None
        # Комиссия 
        try:
            commission_requests = (offer_comission_sum +
                                   accepted_comission_sum +
                                   issued_comission_sum
                                   ) / (issued_comission_sum +
                                        offer_comission_sum +
                                        accepted_comission_sum +
                                        revoked_client_comission_sum +
                                        for_issued_comission_sum
                                        )
        except ZeroDivisionError:
            commission_requests = None
        # Конверсия
        try:
            conversion = (offer_requests.count() +
                          accepted_requests.count() +
                          revoked_client_requests.count() +
                          for_issue_requests.count()
                          ) / all_requests.count()
        except ZeroDivisionError:
            conversion = None

        # C учетом верификации
        try:
            verification_requests = (issued_requests.count() +
                                     offer_requests.count() +
                                     accepted_requests.count() +
                                     revoked_client_requests.count() +
                                     for_issue_requests.count()
                                     ) / (
                                        all_requests.count() - unreached_requests.count()
                                    )
        except ZeroDivisionError:
            verification_requests = None

        # Выдано
        issued = issued_requests

        # Средняя сумма БГ по выданным
        try:
            avg_bg_sum_issued_request = issued_bg_sum / issued_requests.count()
        except ZeroDivisionError:
            avg_bg_sum_issued_request = None

        # Комиссия по выданным
        comissoion_issued = issued_comission_sum

        # Конверсия выданных БГ к выставленным предложений
        try:
            conversion_issued_to_exhibited = issued.count() / (
                issued_requests.count() +
                offer_requests.count() +
                accepted_requests.count() +
                revoked_client_requests.count()
            )
        except ZeroDivisionError:
            conversion_issued_to_exhibited = None

        # Конверсия выданных БГ к выставленым предложений (по объему комиссии)
        try:
            conversion_issued_to_exhibited_by_value = issued_comission_sum / (
                offer_comission_sum +
                issued_comission_sum +
                accepted_comission_sum
            )
        except ZeroDivisionError:
            conversion_issued_to_exhibited_by_value = None

        # Конверсия выданных к "во всех статусах"
        try:
            conversion_issued_to_all = issued.count() / all_requests.count()
        except ZeroDivisionError:
            conversion_issued_to_all = None

        return (avg_bg_sum, commission_requests, conversion, verification_requests,
                issued, avg_bg_sum_issued_request, comissoion_issued,
                conversion_issued_to_exhibited,
                conversion_issued_to_exhibited_by_value, conversion_issued_to_all
                )

    def generate_bank_report(self, date):
        bank_list = Bank.objects.all()

        bank_data = dict()
        overall_unique_result = dict()
        overall_unique_sum_bg = dict()

        for bank in bank_list:
            bank_data[bank.id] = dict()
            overall_unique_result[bank.id] = dict()

            bank_data[bank.id]["name"] = bank.full_name
            requests = Request.objects.filter(bank=bank) \
                .filter(status_changed_date__icontains=date)

            # Во всех статусах (без черновиков)
            bank_data[bank.id]["all_requests"] = requests.exclude(status=26)
            overall_unique_result[bank.id]["all_requests"] = (
                bank_data[bank.id]["all_requests"].filter(
                    base_request__in=Request.objects.values_list('id', flat=True)
                ))
            # Банк направил предложение + выдана+предложение+
            # предложение принято+отклонено клиентом+ на выдачу
            bank_data[bank.id]["requests_done"] = requests.filter(status=9) \
                .filter(status=12) \
                .filter(status=10) \
                .filter(status=14) \
                .filter(status=11)
            overall_unique_result[bank.id]["requests_done"] = (
                bank_data[bank.id]["requests_done"].filter(
                    base_request__in=Request.objects.values_list('id', flat=True)
                ))
            # Не дошло до банка из-за верификации
            bank_data[bank.id]["unreached_requests"] = requests.filter(status=28) \
                .filter(status=29)
            overall_unique_result[bank.id]["unreached_requests"] = (
                bank_data[bank.id]["unreached_requests"].filter(
                    base_request__in=Request.objects.values_list('id', flat=True)
                ))
            # Заявки в статусе Направлена
            directed_requests = requests.filter(status=6)
            directed_requests_unique = directed_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )
            # Заявки в статусе Выдана
            issued_requests = requests.filter(status=12)
            issued_requests_unique = issued_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )
            # Заявки в статусе Предложение
            offer_requests = requests.filter(status=9)
            offer_requests_unique = offer_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )
            # Заявки в статусе Предложение принято
            accepted_requests = requests.filter(status=10)
            accepted_requests_unique = accepted_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )
            # Заявки в статусе Отклонено Клинетом
            revoked_client_requests = requests.filter(status=14)
            revoked_client_requests_unique = revoked_client_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )
            # Заявки в статусе На Выдачу
            for_issue_requests = requests.filter(status=11)
            for_issue_requests_unique = for_issue_requests.filter(
                base_request__in=Request.objects.values_list('id', flat=True)
            )

            bank_data[bank.id]["avg_bg_sum"], \
            bank_data[bank.id]["commission_requests"], \
            bank_data[bank.id]["conversion"], \
            bank_data[bank.id]["verification_requests"], \
            bank_data[bank.id]["issued"], \
            bank_data[bank.id]["avg_bg_sum_issued_request"], \
            bank_data[bank.id]["comissoion_issued"], \
            bank_data[bank.id]["conversion_issued_to_exhibited"], \
            bank_data[bank.id]["conversion_issued_to_exhibited_by_value"], \
            bank_data[bank.id]["conversion_issued_to_all"] = (
                self.get_bank_data(bank_data[bank.id]["all_requests"],
                                   bank_data[bank.id]["requests_done"],
                                   bank_data[bank.id]["unreached_requests"],
                                   directed_requests,
                                   issued_requests,
                                   offer_requests,
                                   accepted_requests,
                                   revoked_client_requests,
                                   for_issue_requests
                                   ))

            overall_unique_result[bank.id]["avg_bg_sum"], \
            overall_unique_result[bank.id]["commission_requests"], \
            overall_unique_result[bank.id]["conversion"], \
            overall_unique_result[bank.id]["verification_requests"], \
            overall_unique_result[bank.id]["issued"], \
            overall_unique_result[bank.id]["avg_bg_sum_issued_request"], \
            overall_unique_result[bank.id]["comissoion_issued"], \
            overall_unique_result[bank.id]["conversion_issued_to_exhibited"], \
            overall_unique_result[bank.id]["conversion_issued_to_exhibited_by_value"], \
            overall_unique_result[bank.id]["conversion_issued_to_all"] = (
                self.get_bank_data(overall_unique_result[bank.id]["all_requests"],
                                   overall_unique_result[bank.id]["requests_done"],
                                   overall_unique_result[bank.id]["unreached_requests"],
                                   directed_requests_unique,
                                   issued_requests_unique,
                                   offer_requests_unique,
                                   accepted_requests_unique,
                                   revoked_client_requests_unique,
                                   for_issue_requests_unique
                                   ))

        overall_data = self.get_overall_result(bank_data)
        overall_data["name"] = "Общий итог"
        overall_unique_data = self.get_overall_result(overall_unique_result)
        overall_unique_data["name"] = "Из них уникальных"

        unique_requests = Request.objects.filter(status_changed_date__icontains=date) \
            .filter(base_request__in=Request.objects.values_list('id', flat=True))
        unique_all_requests = unique_requests.exclude(status=26)
        unique_requests_done = unique_requests.filter(status=9) \
            .filter(status=12) \
            .filter(status=10) \
            .filter(status=14) \
            .filter(status=11)
        unique_issued_requests = unique_requests.filter(status=12)

        overall_unique_sum_bg["name"] = "Сумма БГ по уникальным"
        overall_unique_sum_bg["all_requests"], _ = (
            self.get_bg_and_comission_sum(unique_all_requests))
        overall_unique_sum_bg["requests_done"], _ = (
            self.get_bg_and_comission_sum(unique_requests_done))
        overall_unique_sum_bg["issued"], _ = (
            self.get_bg_and_comission_sum(unique_issued_requests))

        for bank in bank_list:
            bank_data[bank.id]["all_requests"] = (
                bank_data[bank.id]["all_requests"].count())
            bank_data[bank.id]["requests_done"] = (
                bank_data[bank.id]["requests_done"].count())
            bank_data[bank.id]["unreached_requests"] = (
                bank_data[bank.id]["unreached_requests"].count())
            bank_data[bank.id]["issued"] = (
                bank_data[bank.id]["issued"].count())

        result = BankRequestReport(bank_data=bank_data,
                                   overall_data=overall_data,
                                   overall_unique_data=overall_unique_data)
        return result

    def define_business_days(self, date):
        now = datetime.datetime.now()
        now = datetime.date(now.year, now.month, now.day)

        date = datetime.datetime.strptime(date, '%Y-%m')

        holidays = {}
        businessdays = 0
        for i in range(1, 32):
            try:
                thisdate = datetime.date(date.year, date.month, i)
            except(ValueError):
                break
            if (thisdate.weekday() < 5 and thisdate < now and thisdate not in holidays):
                # Monday == 0, Sunday == 6
                businessdays += 1

        return businessdays

    def get_requests_by_amount(self, data):
        requests_dict = dict()

        requests_dict["to_1_mln"] = data \
            .filter(amount__lte=1000000) \
            .aggregate(total=Coalesce(Sum('amount'), 0))["total"]
        requests_dict["1-5_mln"] = data \
            .filter(amount__gt=1000000) \
            .filter(amount__lte=5000000) \
            .aggregate(total=Coalesce(Sum('amount'), 0))["total"]
        requests_dict["5-15_mln"] = data \
            .filter(amount__gt=5000000) \
            .filter(amount__lte=15000000) \
            .aggregate(total=Coalesce(Sum('amount'), 0))["total"]
        requests_dict["from_15_mln"] = data \
            .filter(amount__gt=15000000) \
            .aggregate(total=Coalesce(Sum('amount'), 0))["total"]
        return requests_dict

    def get_structure_report(self, date):
        requests = Request.objects.filter(status_changed_date__icontains=date)

        issued_dict = dict()
        approve_dict = dict()
        offer_dict = dict()
        accepted_dict = dict()
        total_col = dict()

        # Выдана
        issued_requests = Offer.objects.filter(
            request_id__in=requests.filter(status=12).values_list('id', flat=True)
        )
        # Одобрена
        approve_requests = Offer.objects.filter(
            request_id__in=requests.filter(status=20).values_list('id', flat=True)
        )
        # Предложение
        offer_requests = Offer.objects.filter(
            request_id__in=requests.filter(status=9).values_list('id', flat=True)
        )
        # Предложение принятно
        accepted_requests = Offer.objects.filter(
            request_id__in=requests.filter(status=10).values_list('id', flat=True)
        )

        issued_dict = self.get_requests_by_amount(issued_requests)
        approve_dict = self.get_requests_by_amount(approve_requests)
        offer_dict = self.get_requests_by_amount(offer_requests)
        accepted_dict = self.get_requests_by_amount(accepted_requests)

        # Сумма по столбцу
        total_col["to_1_mln"] = (issued_dict["to_1_mln"] +
                                 approve_dict["to_1_mln"] +
                                 offer_dict["to_1_mln"] +
                                 accepted_dict["to_1_mln"])

        total_col["1-5_mln"] = (issued_dict["1-5_mln"] +
                                approve_dict["1-5_mln"] +
                                offer_dict["1-5_mln"] +
                                accepted_dict["1-5_mln"])

        total_col["5-15_mln"] = (issued_dict["5-15_mln"] +
                                 approve_dict["5-15_mln"] +
                                 offer_dict["5-15_mln"] +
                                 accepted_dict["5-15_mln"])

        total_col["from_15_mln"] = (issued_dict["from_15_mln"] +
                                    approve_dict["from_15_mln"] +
                                    offer_dict["from_15_mln"] +
                                    accepted_dict["from_15_mln"])

        # Сумма по строке
        issued_dict["total_row"] = (issued_dict["to_1_mln"] +
                                    issued_dict["1-5_mln"] +
                                    issued_dict["5-15_mln"] +
                                    issued_dict["from_15_mln"])
        approve_dict["total_row"] = (approve_dict["to_1_mln"] +
                                     approve_dict["1-5_mln"] +
                                     approve_dict["5-15_mln"] +
                                     approve_dict["from_15_mln"])
        offer_dict["total_row"] = (offer_dict["to_1_mln"] +
                                   offer_dict["1-5_mln"] +
                                   offer_dict["5-15_mln"] +
                                   offer_dict["from_15_mln"])
        accepted_dict["total_row"] = (accepted_dict["to_1_mln"] +
                                      accepted_dict["1-5_mln"] +
                                      accepted_dict["5-15_mln"] +
                                      accepted_dict["from_15_mln"])
        total_col["total_row"] = (total_col["to_1_mln"] +
                                  total_col["1-5_mln"] +
                                  total_col["5-15_mln"] +
                                  total_col["from_15_mln"])

        result = StructureRequestReport(issued_dict=issued_dict,
                                        approve_dict=approve_dict,
                                        offer_dict=offer_dict,
                                        accepted_dict=accepted_dict,
                                        total_col=total_col)

        return result

    def get_month_dynamics(self, date):
        requests = Request.objects.all()
        month_dynamics = dict()
        month_dynamics["businessdays"] = self.define_business_days(date)

        month_requests = requests.filter(status_changed_date__icontains=date)

        # Кол-во ИНН агента, по которым есть заявки в любом статусе
        month_dynamics["unique_agents"] = month_requests \
            .values_list('agent_id', flat=True) \
            .distinct().count()

        # Кол-во ИНН агента, по которым гарантия выдана
        month_dynamics["unique_agents_issued"] = month_requests \
            .filter(status=12) \
            .values_list('agent_id', flat=True) \
            .distinct().count()

        # Кол-во ИНН клиента  по которым есть заявки в любом статусе
        month_dynamics["unique_clients"] = month_requests \
            .values_list('client_id', flat=True) \
            .distinct().count()

        # Кол-во ИНН клиента, по которым гарантия выдана
        month_dynamics["unique_clients_issued"] = month_requests \
            .filter(status=12) \
            .values_list('client_id', flat=True) \
            .distinct().count()

        # Кол-во уникальных заявок во всех статусах (без учета прошлого месяца)
        month_dynamics["unique_requests_month"] = month_requests \
            .filter(interval_from__icontains=date) \
            .distinct().count()

        # Кол-во уникальных, за исключением черновиков (без заявок прошлого месяца)
        month_dynamics["unique_requests_month_exc_blank"] = month_requests \
            .filter(interval_from__icontains=date) \
            .exclude(status=26) \
            .distinct().count()

        # Кол-во заявок из отчета Максима
        month_dynamics["maxim_report"] = None

        # Кол-во уникальных, за исключением черновиков/кол-во рабочих дней
        month_dynamics["unique_requests_month_exc_blank_to_workday"] = (
            month_dynamics["unique_requests_month_exc_blank"] \
            / month_dynamics["businessdays"]
        )

        # Кол-во заявок из отчета Максима/ на кол-во рабочих дней
        month_dynamics["maxim_report_to_workday"] = None

        # Всего заявок на банки во всех статусах  без черновиков (неуникальных)
        month_dynamics["requests_in_bank"] = month_requests \
            .exclude(bank_id__isnull=True) \
            .exclude(status=26) \
            .count()

        # Кол-во уникальных заявок на банки без черновиков
        month_dynamics["unique_requests_in_bank"] = month_requests \
            .exclude(bank_id__isnull=True) \
            .exclude(status=26) \
            .distinct().count()

        # Выставлено предложений (неуникальных)
        month_dynamics["offer_requests"] = month_requests \
            .filter(status=9) \
            .count()

        # Выставлено предложений (уникальных)
        month_dynamics["unique_offer_requests"] = month_requests \
            .filter(status=9) \
            .distinct().count()

        # Выдано БГ
        month_dynamics["month_issued"] = month_requests \
            .filter(status=12) \
            .count()

        # Конверсия выданных/к зашедшим (уникальные)
        if (month_dynamics["unique_requests_in_bank"] is not None and
                month_dynamics["unique_requests_in_bank"] != 0):
            month_dynamics["conversion_issued_to_unique_requests_in_bank"] = (
                month_dynamics["month_issued"] / month_dynamics["unique_requests_in_bank"]
            )
        else:
            month_dynamics["conversion_issued_to_unique_requests_in_bank"] = 0

        if (month_dynamics["requests_in_bank"] is not None and
                month_dynamics["requests_in_bank"] != 0):
            # Конверсия выданных/к зашедшим (неуникальные)
            month_dynamics["conversion_issued_to_requests_in_bank"] = (
                month_dynamics["month_issued"] / month_dynamics["requests_in_bank"]
            )
            # Конверсия заведено/ выставлено предложений
            month_dynamics["conversion_offer_to_requests_in_bank"] = (
                month_dynamics["offer_requests"] / month_dynamics["requests_in_bank"]
            )
            # Конверсия заведено без черновиков/ выдано
            month_dynamics["conversion_issued_to_requests_in_bank"] = (
                month_dynamics["month_issued"] / month_dynamics["requests_in_bank"]
            )
        else:
            month_dynamics["conversion_issued_to_requests_in_bank"] = 0
            month_dynamics["conversion_offer_to_requests_in_bank"] = 0
            month_dynamics["conversion_issued_to_requests_in_bank"] = 0

        # Конверсия  выставлено предложение/ выдано
        if (month_dynamics["offer_requests"] is not None and
                month_dynamics["offer_requests"] != 0):
            month_dynamics["conversion_offer_to_issued"] = (
                month_dynamics["month_issued"] / month_dynamics["offer_requests"]
            )
        else:
            month_dynamics["conversion_offer_to_issued"] = 0

        # Конверсия  выставлено предложение/ выдано (по уникальным)
        if (month_dynamics["unique_offer_requests"] is not None and
                month_dynamics["unique_offer_requests"] != 0):
            month_dynamics["conversion_offer_to_unique_issued"] = (
                month_dynamics["month_issued"] / month_dynamics["unique_offer_requests"]
            )
        else:
            month_dynamics["conversion_offer_to_unique_issued"] = 0

        if (month_dynamics["unique_agents"] is not None and
                month_dynamics["unique_agents"] != 0):
            # Кол-во уникальных заявок на одного работающего агента
            month_dynamics["unique_request_per_agent"] = (
                month_dynamics["unique_requests_month"] / month_dynamics["unique_agents"]
            )
            # Кол-во уникальных заявок (за исключением черновиков) 
            # на одного работающего агента 
            month_dynamics["unique_requests_exc_blank_per_agent"] = (
                month_dynamics["unique_requests_month_exc_blank"] \
                / month_dynamics["unique_agents"]
            )
        else:
            month_dynamics["unique_request_per_agent"] = 0
            month_dynamics["unique_requests_exc_blank_per_agent"] = 0

        # Кол-во выданных гарантий на 1 агента
        if (month_dynamics["unique_agents_issued"] is not None and
                month_dynamics["unique_agents_issued"] != 0):
            month_dynamics["issued_per_agent_issued"] = (
                month_dynamics["month_issued"] / month_dynamics["unique_agents_issued"]
            )
        else:
            month_dynamics["issued_per_agent_issued"] = 0

        bg_sum, comission_sum = self.get_bg_and_comission_sum(month_requests)
        # Средний чек (сумма БГ)
        try:
            month_dynamics["avg_receipt_bg"] = bg_sum / month_requests.count()
        except ZeroDivisionError:
            month_dynamics["avg_receipt_bg"] = 0

        # Средний чек (комиссия)
        try:
            month_dynamics["avg_receipt_comission"] = comission_sum / (
                month_requests.filter(status__in=[9, 10, 12]).count()
            )
        except ZeroDivisionError:
            month_dynamics["avg_receipt_comission"] = 0

        # Средняя комиссия по выставленным предложениям ( без выданных)
        try:
            month_dynamics["avg_receipt_comission_exc_issued"] = comission_sum / (
                month_requests.filter(status=9).filter(status=10).count()
            )
        except ZeroDivisionError:
            month_dynamics["avg_receipt_comission_exc_issued"] = 0

        # Комиссия млн. руб.
        _, month_dynamics["all_commission_sum"] = (
            self.get_bg_and_comission_sum(month_requests)
        )

        result = MonthDynamicsRequestReport(month_dynamics=month_dynamics, date=date)

        return result

    def get_agent_clients(self, agent):
        return Client.objects.filter(agent_company=agent)

    def get_requests_by_month(self, cur_month, prev_month):
        # Клоичество заявок прошлого месяца
        requests_by_month = dict()
        requests = Request.objects \
            .filter(
            base_request__in=Request.objects.values_list('id', flat=True)) \
            .filter(interval_from__icontains=prev_month) \
            .filter(status_changed_date__icontains=cur_month)
        # Во всех статусах
        requests_by_month["unique_request"] = requests.count()
        # Без Черновиков
        requests_by_month["unique_request_exc_blank"] = (
            requests.exclude(status=26).count())
        return requests_by_month

    def get_total_data(self, manager_data):
        total_result = dict()
        total_result["unique_request"] = 0
        total_result["unique_request_exc_blank"] = 0
        total_result["required_amount"] = 0
        total_result["required_amount_done"] = 0
        total_result["commission_bank"] = 0
        total_result["part_commission_bank"] = 0
        total_result["avg_required_amount"] = 0
        total_result["num_required_amount_done"] = 0
        total_result["avg_term"] = 0
        total_result["conversion"] = 0
        total_result["exhibited"] = 0
        total_result["take_rate"] = 0
        for manager, data in manager_data.items():
            total_result["unique_request"] += data["unique_request"]
            total_result["unique_request_exc_blank"] += data["unique_request_exc_blank"]
            total_result["required_amount"] += data["required_amount"]
            total_result["required_amount_done"] += data["required_amount_done"]
            total_result["commission_bank"] += data["commission_bank"]
            total_result["part_commission_bank"] += data["part_commission_bank"]
            total_result["avg_required_amount"] += data["avg_required_amount"]
            total_result["num_required_amount_done"] += data["num_required_amount_done"]
            total_result["avg_term"] += data["avg_term"]
            total_result["conversion"] += data["conversion"]
            total_result["exhibited"] += data["exhibited"]
            total_result["take_rate"] += data["take_rate"]
        return total_result

    @drf_action(detail=False, methods=['POST', 'GET'])
    def generate_manager_statistics_report(self, *args, **kwargs):
        data = dict()
        total_data = dict()
        requests_to_businessdays = dict()

        date = self.request.data.get('date')

        cur_month = datetime.datetime.strptime(date, '%Y-%m')
        prev = cur_month.replace(day=1) - datetime.timedelta(days=1)
        prev_month = str(prev.year) + "-" + str(prev.month)

        bank_statistic_data = self.generate_bank_report(date)
        month_dynamics = self.get_month_dynamics(date)
        structure_data = self.get_structure_report(date)

        managers_list_id = list()
        # Извлечение списка менеджеров
        managers_list = AgentManager.get_managers()
        for manager in managers_list.values():
            managers_list_id.append(manager["id"])

        all_commission_bank = 0
        for manager_id in managers_list_id:
            interval = 1
            # Создание словоря с информацией по каждому менеджеру
            data[manager_id] = dict()
            data[manager_id]["name"] = managers_list.get(id=manager_id).first_name
            data[manager_id]["agent_list"] = list()
            data[manager_id]["client_list"] = list()
            data[manager_id]["request_list"] = list()
            data[manager_id]["unique_request"] = 0
            data[manager_id]["unique_request_exc_blank"] = 0

            data[manager_id]["required_amount"] = 0
            data[manager_id]["required_amount_done"] = 0
            data[manager_id]["num_required_amount_done"] = 0
            data[manager_id]["commission_bank"] = 0
            data[manager_id]["part_commission_bank"] = 0
            data[manager_id]["avg_required_amount"] = 0
            data[manager_id]["conversion"] = 0
            data[manager_id]["exhibited"] = 0
            data[manager_id]["take_rate"] = 0

            # Получение списка агентов, прикрепленных к менеджеру
            agent_list = AgentManager.get_manager_agents(manager_id)
            data[manager_id]["agent_list"] = agent_list

            # Получение списка клиентов, закрепленных за агентами
            for agent in data[manager_id]["agent_list"]:
                client_list = self.get_agent_clients(agent)
                if client_list.exists():
                    data[manager_id]["client_list"] += client_list

            # Получение списка заявок, прикрепеленных за клиентами
            for client in data[manager_id]["client_list"]:
                request_list = Request.objects \
                    .filter(client=client) \
                    .filter(status_changed_date__icontains=date)
                unique_request_list = request_list.filter(
                    base_request__in=Request.objects.values_list('id', flat=True)
                )

                # Уникальные заявки (Во всех статусах)
                data[manager_id]["unique_request"] += unique_request_list.count()

                # Уникальные заявки (Кроме Черновиков)
                data[manager_id]["unique_request_exc_blank"] += (
                    unique_request_list.exclude(status=26).count())

                # Сумма БГ (Кроме Черновиков)
                data[manager_id]["required_amount"] += Offer.objects.filter(
                    request_id__in=unique_request_list.exclude(
                        status=26
                    ).values_list('id', flat=True)).aggregate(
                    total=Coalesce(Sum('amount'), 0)
                )["total"]
                # Сумма БГ (по Выданнам заявкам)
                data[manager_id]["required_amount_done"] += Offer.objects.filter(
                    request_id__in=unique_request_list.filter(
                        status=12
                    ).values_list('id', flat=True)).aggregate(
                    total=Coalesce(Sum('amount'), 0)
                )["total"]
                # Количество всех выданных БГ
                data[manager_id]["num_required_amount_done"] += unique_request_list \
                    .filter(status=12) \
                    .count()
                # Комиссия банка по выданным БГ
                data[manager_id]["commission_bank"] += Offer.objects.filter(
                    request_id__in=unique_request_list.filter(
                        status=12
                    ).values_list('id', flat=True)).aggregate(
                    total=Coalesce(Sum('commission_bank'), 0)
                )["total"]
                # Выставлено предложений
                data[manager_id]["exhibited"] += RequestHistory.objects \
                    .filter(request_id__in=Request.objects \
                            .filter(client=client) \
                            .filter(status_changed_date__icontains=date) \
                            .values_list('id', flat=True)) \
                    .count()

                interval += unique_request_list \
                    .aggregate(total=Coalesce(Sum('interval'), 0))["total"]

            all_commission_bank = Offer.objects.filter(
                request_id__in=Request.objects.filter(
                    status_changed_date__icontains=date
                ).values_list('id', flat=True)
            ).aggregate(total=Coalesce(Sum('commission_bank'), 0))["total"]

            # Доля по комиссии Банка
            if all_commission_bank is not None and all_commission_bank != 0:
                data[manager_id]["part_commission_bank"] = (
                    data[manager_id]["commission_bank"] / all_commission_bank
                )
            # Средняя сумма БГ по выданным
            if (data[manager_id]["num_required_amount_done"] is not None and
                    data[manager_id]["num_required_amount_done"] != 0):
                data[manager_id]["avg_required_amount"] = (
                    data[manager_id]["required_amount_done"]
                    / data[manager_id]["num_required_amount_done"]
                )
            # Средний срок БГ
            data[manager_id]["avg_term"] = data[manager_id]["unique_request"] / interval
            # Конверсия
            if (data[manager_id]["unique_request_exc_blank"] is not None and
                    data[manager_id]["unique_request_exc_blank"] != 0):
                data[manager_id]["conversion"] = (
                    data[manager_id]["num_required_amount_done"]
                    / data[manager_id]["unique_request_exc_blank"]
                )
            # TakeRate
            if (data[manager_id]["exhibited"] is not None and
                    data[manager_id]["exhibited"] != 0):
                data[manager_id]["take_rate"] = (
                    data[manager_id]["num_required_amount_done"] /
                    data[manager_id]["exhibited"]
                )

            del data[manager_id]["agent_list"]
            del data[manager_id]["client_list"]

        # Общий итог
        total_data = self.get_total_data(data)
        total_data["name"] = "Общий итог"

        # Без заявок прошлого месяца
        requests_without_last_month = self.get_requests_by_month(date, date)
        requests_without_last_month["name"] = "Без заявок прошлого месяца"

        # Количество заявок прошлого месяца
        requests_last_month = self.get_requests_by_month(date, prev_month)
        requests_last_month["name"] = "Клоичество заявок прошлого месяца"

        # Среднее кол-во заявок в р.д. 
        requests_to_businessdays["unique_request"] = self.define_business_days(date)
        requests_to_businessdays["unique_request_exc_blank"] = (
            (total_data["unique_request_exc_blank"] - \
             requests_last_month["unique_request_exc_blank"])
            / self.define_business_days(date))
        requests_to_businessdays["name"] = "Среднее кол-во заявок в р.д."

        result = ManagerRequestReport(
            manager_data=data,
            total_data=total_data,
            requests_last_month=requests_last_month,
            requests_without_last_month=requests_without_last_month,
            requests_to_businessdays=requests_to_businessdays,
            bank_statistic_data=bank_statistic_data,
            month_dynamics=month_dynamics,
            structure_data=structure_data
        ).generate()

        return Response({
            'data': data,
            'report': result.file_path,
            'name': result.output_name,
        })

    @drf_action(detail=False, methods=['GET'])
    def additional(self, request):
        type_products = [
            {
                'label': 'Банковская гарантия',
                'value': ProductChoices.PRODUCT_BG
            },
            {
                'label': 'Тендерный займ',
                'value': ProductChoices.PRODUCT_LOAN
            },
            {
                'label': 'Все',
                'value': ProductChoices.PRODUCT_ALL
            }
        ]
        managers = UserForSelectInput(
            User.objects.filter(roles__name=Role.MANAGER),
            many=True
        ).data
        managers.append({'label': 'Все', 'value': 'all'})
        return Response({
            'type_products': type_products,
            'managers': managers,
        })

    @drf_action(methods=['GET'], detail=False)
    def get_agents(self, request):
        if request.query_params.get('manager'):
            if request.query_params['manager'] != 'all':
                agents = Agent.objects.filter(
                    manager__manager=request.query_params['manager']
                )
            else:
                agents = Agent.objects.all()
            return Response({
                'agents': AgentSerializerForSelectInput(agents, many=True).data
            })
        return Response({
            'error': 'Выберите менеджера'
        })

    @drf_action(methods=['GET'], detail=False)
    def accepted_contract_agents(self, request):
        if self.request.user.has_role('admin'):
            return Response({
                'agent_contracts': [{
                    'id': contract.id,
                    'agent_id': contract.agent.id,
                    'agent_inn': contract.agent.inn,
                    'agent_short_name': contract.agent.short_name,
                    'accept_contract': contract.accept_contract,
                    'accept_contract_date': contract.accept_date,
                    'contract_date': contract.contract.start_date,
                    'contract_name': contract.contract.name,
                } for contract in AgentContractOffer.objects.order_by('-accept_date')]
            })
        if self.request.user.client.get_role() == Agent.__name__:
            return Response(
                {
                    'agent_contracts': [
                        {
                            'name': contract.contract.name,
                            'url': contract.contract.file.url,
                            'accept_contract': {
                                True: 'Принят',
                                False: 'Отказ',
                                None: 'Без ответа'
                            }.get(contract.accept_contract),
                            'accept_date': contract.accept_date.strftime(
                                '%d.%m.%Y'
                            ) if contract.accept_date else '',
                        } for contract in AgentContractOffer.objects.filter(
                            agent=self.request.user.client.get_actual_instance
                        ).order_by('-accept_date')
                    ]
                }
            )
