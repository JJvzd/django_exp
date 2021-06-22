from datetime import datetime

from django.db import models

from cabinet.constants.constants import OrganizationForm
from cabinet.models import Region, EgrulData
from clients.models import Company, AgentManager
from common.helpers import get_logger
from external_api.dadata_api import DaData
from external_api.helper import get_dict_to_path
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from questionnaire.models import (
    ProfilePartnerIndividual, PassportDetails, ProfilePartnerLegalEntities,
    LicensesSRO, KindOfActivity, DocumentGenDir
)

logger = get_logger()


class Client(Company):
    agent_company = models.ForeignKey(
        to='Agent', on_delete=models.SET_NULL,
        null=True, db_index=True
    )
    agent_user = models.ForeignKey(
        to='users.User', related_name='related_clients', on_delete=models.SET_NULL,
        null=True, db_index=True
    )
    date_last_action = models.DateField(
        verbose_name='Дата последнего действия',
        blank=True,
        null=True
    )
    winner_notification = models.BooleanField(
        default=True, verbose_name='Уведомления о победе'
    )
    manager = models.ForeignKey(
        to='users.User', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='client_managers'
    )
    manager_fio = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="ФИО менеджера"
    )

    def change_agent(self, agent_company, agent_user,
                     reattach_exists_requests=False):
        from clients.helpers import ChangeAgentValidator
        self.agent_company = agent_company
        self.agent_user = agent_user
        manager = AgentManager.get_manager_by_agent(agent_company)
        self.manager = manager
        self.save()
        if reattach_exists_requests:
            helper = ChangeAgentValidator(self)
            requests = helper.get_working_requests()
            requests.update(agent=agent_company, agent_user=agent_user)
        return True

    @property
    def accounting_report(self):
        from accounting_report.logic import AccountingReport
        return AccountingReport(self)

    def fill_questionnaire(self, file=None):  # noqa: MC0001

        if self.profile and not self.profile.reg_inn:
            logger.info('Анкеты не существует или не заполнено поле ИНН')
            return False

        data = EgrulData.get_info(self.profile.reg_inn)

        if not data:
            logger.error('Ошибка при заполнении анкеты из ЕГРЮЛ')
            return False

        profile = self.profile

        values = {
            'authorized_capital_paid': 'section-capital.paid-uk',
            'authorized_capital_announced': 'section-capital.declared-uk',
            "reg_kpp": "section-gos-reg.kpp",
            "reg_ogrn": "section-gos-reg.ogrn",
            "full_name": "section-ur-lico.full-name-ur-lico",
            "short_name": "section-ur-lico.short-name-url-lico",
        }

        for key, value in values.items():
            value_data = get_dict_to_path(data, value, default=None) or None
            setattr(profile, key, value_data)
        profile.legal_address = get_dict_to_path(
            data,
            'section-ur-adress.full_address',
            default=''
        )

        api = DaData()
        data_dadata = api.get_company(self.profile.reg_inn).get('suggestions', [{}])[0]
        values_dadata = {
            'reg_okato': 'data.address.data.okato',
            'code_oktmo': 'data.address.data.oktmo',
            'reg_okpo': 'data.okpo',
        }
        for key, value in values_dadata.items():
            value_data = get_dict_to_path(data_dadata, value,
                                          default=None) or None
            if value_data:
                setattr(profile, key, value_data)
        # информация по гендиру
        boss = data.get('section-boss-data')
        boss_inn = boss.get('innboss')

        general_director = ProfilePartnerIndividual.objects.filter(
            profile=profile,
            is_general_director=True).first()
        if not general_director:
            general_director = ProfilePartnerIndividual(
                profile=profile, is_general_director=True
            )
        # удаление предыдущего гендира, если понадобится
        elif general_director.fiz_inn != boss_inn:
            general_director.delete()
            general_director = ProfilePartnerIndividual(
                profile=profile, is_general_director=True
            )
        else:
            pass

        accept_partners = []
        # Обновление полей генерального директора
        gen_dir_data = {
            'is_general_director': True,
            # 'is_booker': True,
            'gen_dir_post': boss.get('positionboss'),
            'fiz_inn': boss_inn,
            'name': boss.get('fio'),
            'profile': profile,
            'last_name': boss.get('last_name'),
            'first_name': boss.get('first_name'),
            'middle_name': boss.get('middle_name'),
        }

        for field in gen_dir_data:
            setattr(general_director, field, gen_dir_data[field])

        if general_director.passport is None:
            general_director.passport = PassportDetails.objects.create()

        general_director.save()
        try:
            general_director.document_gen_dir
        except Exception:
            DocumentGenDir.objects.create(person=general_director)
        general_director_id = general_director.id
        accept_partners.append(general_director_id)

        # физические лица
        individual_partners = get_dict_to_path(
            data, 'section-akcionery_fiz.akcionery_fiz', default=[]
        )
        for individual_partner in individual_partners:
            fiz_inn = individual_partner.get('innfl')
            person, created = ProfilePartnerIndividual.objects.get_or_create(
                profile=profile,
                fiz_inn=fiz_inn)
            share = individual_partner.get('percents')

            if '/' in str(share):
                parts = share.split('/')
                share = int(parts[0]) / int(parts[1]) * 100
            if not share or float(share) < 1:
                continue

            if general_director_id == person.id:
                person.share = share
                person.is_beneficiary = True
                person.save()

                accept_partners.append(person.id)

            else:
                # Заполнение полей физического лица
                person.last_name = individual_partner.get('last_name')
                person.first_name = individual_partner.get('first_name')
                person.middle_name = individual_partner.get('middle_name')
                person.is_beneficiary = True
                person.share = share
                if person.passport is None:
                    person.passport = PassportDetails.objects.create()
                person.save()

                accept_partners.append(person.id)

        # Удаление отсутствующих физическиз лиц

        for partner in ProfilePartnerIndividual.objects.filter(profile=profile):
            if partner.id not in accept_partners:
                partner.delete()

        # Заполнение полей юридических лиц
        legal_partners_data = get_dict_to_path(data,
                                               'section-akcionery_yur.akcionery_yur',
                                               [])
        all_legal_partners = ProfilePartnerLegalEntities.objects.filter(
            profile=profile)
        accept_legal_partners = []

        for legal_partner_data in legal_partners_data:
            legal_partner = (ProfilePartnerLegalEntities.objects.filter(
                inn=legal_partner_data.get('inn_yur'),
                profile=profile).first()) or (
                                ProfilePartnerLegalEntities(
                                    inn=legal_partner_data.get('inn_yur'),
                                    profile=profile)
                            )
            legal_partner.share = legal_partner_data.get('percents') or 0
            legal_partner.name = legal_partner_data.get('name_yur')
            legal_partner.ogrn = legal_partner_data.get('ogrn_yur')
            legal_partner.save()
            accept_legal_partners.append(legal_partner.id)

        # Удаление ненужных юридических диц
        for legal_partner in all_legal_partners:
            if legal_partner.id not in accept_legal_partners:
                legal_partner.delete()

        # Добавления Лицензий СРО
        licenses_data = get_dict_to_path(data, 'section-licenzies.licenzies',
                                         [])
        all_licenses = LicensesSRO.objects.filter(profile=profile)
        accept_licenses = []

        if licenses_data:
            self.profile.has_license_sro = True

            for license_data in licenses_data:
                number_license = license_data.get('number-licenzies')
                license_sro = LicensesSRO.objects.filter(
                    profile=profile, number_license=number_license
                ).first() or LicensesSRO(
                    profile=profile,
                    number_license=number_license
                )
                license_sro.view_activity = license_data.get(
                    'section-vid-action')
                license_sro.date_issue_license = (license_data.get(
                    'date-start-licenzies') or None) and datetime.strptime(
                    license_data.get('date-start-licenzies'), '%d.%m.%Y').date()
                license_sro.date_end_license = (license_data.get(
                    'date-finish-licenzies') or None) and datetime.strptime(
                    license_data.get('date-finish-licenzies'),
                    '%d.%m.%Y').date()
                license_sro.issued_by_license = license_data.get(
                    'licensing-authority')
                license_sro.list_of_activities = ''
                license_sro.save()
                accept_licenses.append(license_sro.id)
        else:
            self.profile.has_license_sro = False

        # Удаление ненужных Лицензий СРО
        for license_sro in all_licenses:
            if license_sro.id not in accept_licenses:
                license_sro.delete()

        # первый вид деятельности (основной)
        data_activity = data.get('section-vid-actions')
        if data_activity:
            activity = data_activity[0]
        else:
            activity = None

        if activity:
            view_activity = KindOfActivity.objects.filter(
                profile=profile,
                value=activity
            ).first()
            if not view_activity:
                KindOfActivity(
                    profile=profile,
                    value=activity
                ).save()

        # Дата регистрации компании
        register_date = get_dict_to_path(data,
                                         'section-register.date-gos-register')
        profile.reg_state_date = datetime.strptime(register_date,
                                                   '%d.%m.%Y').date()

        # Организационно-правовая форма
        if profile.short_name:
            for code, name in OrganizationForm.CHOICES:
                if profile.short_name.startswith(name):
                    profile.organization_form = code

        zachestnyi = ZaChestnyiBiznesApi()
        data = zachestnyi.method('card', profile.reg_inn)
        # Среднесписочная численность на дату заполнения
        if data.get('ЧислСотруд'):
            profile.number_of_employees = data['ЧислСотруд']
        else:
            profile.number_of_employees = 1
        # Среднемесячный фонд оплаты труда, руб.
        if data.get('ФондОплТруда'):
            profile.salary_fund = data['ФондОплТруда']
        else:
            profile.salary_fund = 15000

        # Сохранение анкеты
        profile.save()
        logger.info(
            'Анкета клиента %s успешно обновлена из ЕГРЮЛ' % profile.full_name)

    def update_kpp_ogrn_region(self):
        if self.kpp:
            self.region = Region.get_region(kpp=self.kpp)
        elif self.inn:
            self.region = Region.get_region(inn=self.inn)
        if not self.region:
            logger.error(
                'Регион не определился для пользователя с ИНН: %s' % self.inn
            )
        self.save()

    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'


class ClientChangeAgentHistory(models.Model):
    client = models.ForeignKey(to=Client, on_delete=models.CASCADE)
    agent_company = models.ForeignKey(to='Agent', on_delete=models.CASCADE)
    agent_user = models.ForeignKey(to='users.User', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)


class TenderHelpAgentComment(models.Model):
    comment = models.TextField(verbose_name='Текст комментария', )
    create_time = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания'
    )
    user = models.ForeignKey(to='users.User', on_delete=models.CASCADE)

    def __str__(self):
        return '%s %s %s' % (self.id, self.create_time, self.user)

    class Meta:
        ordering = ['-id', ]
        verbose_name = 'TenderHelpAgentComment'
        verbose_name_plural = 'TenderHelpAgentComment'
