from django.db.models import Q
from rest_framework import serializers, fields
from rest_framework.fields import SerializerMethodField

from accounting_report.serializers import QuarterSerializerInbank
from bank_guarantee.models import (
    Request, Offer, Discuss, ClientDocument, Message, MessageFile, RequestHistory,
    OfferDocumentCategory, OfferDocument, RequestDocument, RequestedCategory,
    OfferPrintForm, BankRatingResult, BankOfferDocumentCategory, TempOfferDoc
)
from base_request.models import RequestTender, BankDocumentType
from base_request.serializers import RequestStatusSerializer, RequestTenderSerializer
from cabinet.constants.constants import Target
from cabinet.models import PlacementPlace
from cabinet.serializers import (
    FileSerializer, CertificateSerializer, ProfileSerializerInbank
)
from calculator.models import CalculatorRule
from calculator.serializers import CalculatorRuleSerializer
from clients.serializers import (
    BankSerializer, AgentSerializer, ClientSerializer, CompanySerializer
)
from settings.configs.other import PASSPORT_ID
from users.models import Role, User
from users.serializers import UserSerializer


class MessageFileSerializer(serializers.ModelSerializer):
    file = FileSerializer(read_only=True)

    class Meta:
        model = MessageFile
        fields = [
            'file',
        ]


class MessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    files = MessageFileSerializer(read_only=True, many=True, source='files.all')

    class Meta:
        model = Message
        fields = [
            'author',
            'message',
            'created',
            'files',
        ]


class DiscussSerializer(serializers.ModelSerializer):
    bank = BankSerializer(read_only=True)
    agent = AgentSerializer(read_only=True)
    client = ClientSerializer(read_only=True, source='request.client')

    class Meta:
        model = Discuss
        fields = [
            'id',
            'bank',
            'agent',
            'client',
        ]


class OfferDocumentCategorySerializer(serializers.ModelSerializer):
    print_form = serializers.SerializerMethodField('get_print_form')

    def get_print_form(self, obj):
        if self.context.get('request'):
            result = BankOfferDocumentCategory.objects.filter(
                bank=self.context['request'].bank,
                category=obj
            ).first()
            if result:
                return OfferDocumentPrintFormSerializer(
                    result.print_form,
                    context=self.context
                ).data

    class Meta:
        model = OfferDocumentCategory
        fields = [
            'id',
            'name',
            'order',
            'step',
            'required',
            'active',
            'print_form'
        ]


class OfferDocumentPrintFormSerializer(serializers.ModelSerializer):
    temp_file = serializers.SerializerMethodField('get_temp_file')

    def get_temp_file(self, obj):
        if self.context.get('request') and self.context['request'].has_offer():
            result = TempOfferDoc.objects.filter(
                offer=self.context['request'].offer,
                print_form=obj
            ).first()
            if result:
                return FileSerializer(result.file).data

    class Meta:
        model = OfferPrintForm
        fields = (
            'id',
            'name',
            'temp_file'
        )


class OfferDocumentSerializer(serializers.ModelSerializer):
    file = FileSerializer()
    category = OfferDocumentCategorySerializer
    client_sign = serializers.SerializerMethodField(method_name='get_client_sign')
    client_old_sign = serializers.SerializerMethodField(method_name='get_client_old_sign')
    bank_sign = serializers.SerializerMethodField(method_name='get_bank_sign')
    bank_old_sign = serializers.SerializerMethodField(method_name='get_bank_old_sign')

    def get_client_sign(self, object):
        if object.file:
            sign = object.file.sign_set.filter(author=object.offer.request.client).first()
            if sign:
                return {
                    'sign_file': sign.signed_file.url,
                    'sign_name': sign.signed_file.filename,
                    'created': sign.signed_date,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    def get_client_old_sign(self, object):
        if object.file:
            sign = object.file.separatedsignature_set.filter(
                author=object.offer.request.client
            ).first()
            if sign:
                return {
                    'sign_file': sign.sign,
                    'created': sign.created,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    def get_bank_sign(self, object):
        if object.file:
            sign = object.file.sign_set.filter(author=object.file.author).first()
            if sign:
                return {
                    'sign_file': sign.signed_file.url,
                    'sign_name': sign.signed_file.filename,
                    'created': sign.signed_date,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    def get_bank_old_sign(self, object):
        if object.file:
            sign = object.file.separatedsignature_set.first()
            if sign:
                return {
                    'sign_file': sign.sign,
                    'created': sign.created,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    class Meta:
        model = OfferDocument
        fields = [
            'id',
            'file',
            'category',
            'client_sign',
            'client_old_sign',
            'bank_sign',
            'bank_old_sign',
        ]


class OfferSerializer(serializers.ModelSerializer):
    documents = OfferDocumentSerializer(source='offerdocument_set.all', many=True)

    additional_data = serializers.SerializerMethodField('get_additional_data')
    calculator = serializers.SerializerMethodField()

    def get_additional_data(self, obj):
        return obj.get_additional_data

    def get_calculator(self, obj):
        q = Q()
        for target in obj.request.targets: q &= Q(targets__contains=target)
        calculator = CalculatorRule.objects.filter(
            calculator__credit_organization_code=obj.request.bank.code,
            law=obj.request.tender.federal_law).filter(q).last()
        serializer = CalculatorRuleSerializer(calculator)
        return serializer.data

    class Meta:
        model = Offer
        fields = [
            'id',
            'amount',
            'offer_active_end_date',
            'contract_date_end',
            'contract_number',
            'contract_date',
            'registry_number',
            'commission',
            'default_commission',
            'delta_commission',
            'commission_bank',
            'default_commission_bank',
            'default_commission_bank_percent',
            'delta_commission_bank',
            'commission_bank_percent',
            'created',
            'updated',
            'documents',
            # 'additional_fields',
            'additional_data',
            'require_insurance',
            'request',
            'ruchnaya_korrect',
            'kv_previsheniya',
            'reduction_agent',
            'reduction_bank',
            'calculator',
        ]


class RequestSerializer(serializers.ModelSerializer):
    """Сериализационная модель заявок"""
    status = RequestStatusSerializer(read_only=True)
    tender = RequestTenderSerializer()
    offer = OfferSerializer(read_only=True)
    bank = BankSerializer(read_only=True)
    agent = AgentSerializer(read_only=True)
    assigned = UserSerializer(read_only=True)
    verifier = UserSerializer(read_only=True)
    client = ClientSerializer(read_only=True)
    targets = fields.MultipleChoiceField(choices=Target.CHOICES)
    offer_additional_fields = serializers.ReadOnlyField(
        source='get_offer_additional_fields'
    )
    additional_status = serializers.ReadOnlyField()
    decision_maker = serializers.SerializerMethodField('get_decision_maker')

    rating = SerializerMethodField()

    def get_decision_maker(self, instance):
        result = instance.requestassignedhistory_set.filter(
            assigner__roles__name=Role.BANK_DECISION_MAKER
        ).order_by('created').last()
        if result:
            return UserSerializer(result.assigner).data

    def update(self, instance, validated_data):
        tender_data = validated_data.pop('tender')
        if tender_data['placement']['name']:
            tender_data['placement'] = PlacementPlace.find_or_insert(
                name=tender_data['placement']['name']
            )
        else:
            tender_data.pop('placement')
        if validated_data['contract_type'] != 'commercial':
            tender_url = RequestTender.generate_url(
                tender_data.get('tender_url'),
                tender_data.get('federal_law'),
                tender_data.get('notification_id')
            )
            if tender_url:
                tender_data['tender_url'] = tender_url
        tender_data = {key: val for key, val in tender_data.items() if
                       val is not fields.empty}
        RequestTender.objects.filter(id=instance.tender_id).update(**tender_data)
        Request.objects.filter(id=instance.id).update(**validated_data)

        return Request.objects.filter(id=instance.id).first()

    def get_rating(self, obj):
        rating_result = obj.bankratingresult_set.filter().last()
        return BankRatingResultSerializer(rating_result).data

    class Meta:
        model = Request
        fields = (
            'id',
            'tender',
            'currency',
            'have_additional_requirement',
            'required_amount',
            'procuring_amount',
            'suggested_price_amount',
            'suggested_price_percent',
            'prepaid_expense_amount',
            'downpay',
            'term_of_work_to',
            'term_of_work_from',
            'final_date',
            'contract_type',
            'placement_way',
            'placement_way_other',
            'protocol_number',
            'protocol_date',
            'protocol_lot_number',
            'protocol_territory',
            'status',
            'status_changed_date',
            'warranty_from',
            'warranty_to',
            'interval_from',
            'interval_to',
            'interval',
            'package_class',
            'package_categories',
            'tmp_manager',
            'client',
            'bank',
            'agent',
            'agent_user_id',
            'additional_requirement',
            # 'anketa',
            'scoring_reject_reason',
            'targets',
            'base_request',
            'request_number',
            'banks_commissions',
            'in_archive',
            'is_big_deal',
            'agree',
            'need_client',
            'need_agent',
            'need_bank',
            'power_of_attorney',
            'experience_general_contractor',
            'questionnaire_was_updated',
            'bo_was_updated',
            'is_signed',
            # 'received_guarantee',
            'bank_reject_reason',
            'last_comment',
            'request_number_in_bank',
            'sent_to_bank_date',
            'created_date',
            'updated_date',
            'offer',
            'agree',
            'offer_additional_fields',
            'assigned',
            'additional_status',

            'creator_name',
            'creator_phone',
            'creator_phone_additional',
            'creator_email',

            'rating',
            'decision_maker',
            'verifier',
        )


class BankRatingResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankRatingResult
        fields = ('risk_level', 'score', 'rating', 'finance_state')


class RequestOffersSerializer(serializers.ModelSerializer):
    """Сериализационная модель предложение заявок"""

    class Meta:
        model = Offer
        fields = (
            'id',
            'commission',
            'default_commission',
            'delta_commission',
            'summa_bg',
            'request',
            'status',
            'bank',
            'status_changed',
            'date_active',
            'date_bg',
            'valuta',
            'variant',
            'address_type',
            'other_address',
            'contract_number',
            'contract_date',
            'created',
            'update_date',
        )


class ShortRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = [
            'id',
            'request_number',
            'request_number_in_bank',
        ]


class ShortDiscussSerializer(serializers.ModelSerializer):
    """Сериализационная модель дискусии"""
    bank = BankSerializer(read_only=True)
    client = ClientSerializer(read_only=True, source='request.client')
    message_count = serializers.ReadOnlyField(source='messages.all.count', read_only=True)
    request = ShortRequestSerializer(read_only=True)

    class Meta:
        model = Discuss
        fields = (
            'id',
            'request',
            'bank',
            'client',
            'message_count',
        )


class ClientDocumentSerializer(serializers.ModelSerializer):
    """Сериализационная модель документов киентов"""
    file = FileSerializer()

    class Meta:
        model = ClientDocument
        fields = (
            'id',
            'client',
            'file',
        )


class RequestHistorySerializer(serializers.ModelSerializer):
    status = RequestStatusSerializer(read_only=True)
    user = serializers.SerializerMethodField('get_user')
    client = serializers.SerializerMethodField('get_company')
    created = serializers.DateTimeField(read_only=True)

    def __user_for_obj(self, obj):
        request = self.context.get('request')
        user = obj.user
        if (request.user.client.get_role() == 'Bank' and
                user.client.get_role() == 'Agent'):
            user = User.objects.get(username='tenderhelp')
        return user

    def get_user(self, obj):
        user = self.__user_for_obj(obj)
        if user:
            return UserSerializer(user).data

    def get_company(self, obj):
        user = self.__user_for_obj(obj)
        if user:
            return CompanySerializer(user.client).data if user else {}

    class Meta:
        model = RequestHistory
        fields = [
            'action',
            'user',
            'comment',
            'status',
            'created',
            'client',
        ]


class BankDocumentTypeSerializer(serializers.ModelSerializer):
    passport_beneficiary = serializers.SerializerMethodField(
        method_name='get_passport_beneficiary')

    def get_passport_beneficiary(self, object):
        return object.id == PASSPORT_ID

    class Meta:
        model = BankDocumentType
        fields = [
            'id',
            'name',
            'download_name',
            'active',
            'order',
            'position',
            'passport_beneficiary',
        ]


class RequestDocumentSerializer(serializers.ModelSerializer):
    """Сериализатор для модели RequestDocument"""
    cert = CertificateSerializer(read_only=True, source='certificate')
    file = FileSerializer(read_only=True)
    category = BankDocumentTypeSerializer()
    requested_category_id = serializers.IntegerField()
    person = serializers.SerializerMethodField('get_person')

    sign = serializers.SerializerMethodField(method_name='get_sign')
    old_sign = serializers.SerializerMethodField(method_name='get_old_sign')

    def get_person(self, obj):
        link = obj.documentlinktoperson_set.first()
        if link:
            return link.person.id

    def get_sign(self, object):
        if object.file:
            author = object.request.client
            sign = object.file.sign_set.filter(author=author).first()
            if sign:
                return {
                    'sign_file': sign.signed_file.url,
                    'sign_name': sign.signed_file.filename,
                    'created': sign.signed_date,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    def get_old_sign(self, object):
        if object.file:
            sign = object.file.separatedsignature_set.first()
            if sign:
                return {
                    'sign_file': sign.sign,
                    'created': sign.created,
                    'certificate': CertificateSerializer(sign.certificate).data
                }
        return {}

    class Meta:
        model = RequestDocument
        fields = (
            'id',
            'request',
            'file',
            'category',
            'cert',
            'sign',
            'old_sign',
            'sign_date',
            'print_form',
            'requested_category_id',
            'person',
        )


class BaseShortDiscussSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    request_type = serializers.CharField(read_only=True)
    last_message = serializers.DateTimeField(read_only=True)
    request_id = serializers.IntegerField(read_only=True, source='request__id')
    request_number = serializers.CharField(
        read_only=True, source='request__request_number'
    )
    request_number_in_bank = serializers.CharField(
        read_only=True, source='request__request_number_in_bank'
    )
    bank__short_name = serializers.CharField(read_only=True)
    client__short_name = serializers.CharField(
        read_only=True, source='request__client__short_name'
    )
    client__inn = serializers.CharField(read_only=True, source='request__client__inn')
    message_count = serializers.IntegerField(read_only=True)


class RequestCommentSerializer(serializers.Serializer):
    request = serializers.ImageField(read_only=True)
    bank = serializers.CharField(read_only=True, source='bank.name')
    text = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)


"""Сериализаторы для ИНБАНКА"""


class TenderSerializerInbank(serializers.ModelSerializer):
    notification_id = serializers.CharField(read_only=True)
    publish_date = serializers.DateField(read_only=True, format='%d.%m.%Y')
    subject = serializers.CharField(read_only=True)
    federal_law = serializers.CharField(source='get_federal_law_display', read_only=True)
    start_price = serializers.DecimalField(
        source='price', read_only=True, max_digits=20, decimal_places=2
    )
    customer = serializers.SerializerMethodField('get_customer')

    def get_customer(self, tender):
        return {
            'name': tender.beneficiary_name,
            'inn': tender.beneficiary_inn,
            'kpp': tender.beneficiary_kpp,
            'ogrn': tender.beneficiary_ogrn,
            'placement': tender.placement.name if tender.placement else '',
        }

    class Meta:
        model = RequestTender
        fields = (
            'notification_id',
            'publish_date',
            'subject',
            'federal_law',
            'start_price',
            'customer',

        )


class RequestSerializerInbank(serializers.ModelSerializer):
    request_number = serializers.SerializerMethodField('get_request_number')
    anketa_id = serializers.IntegerField(source='client.profile.id', read_only=True)
    accounting_report_id = serializers.IntegerField(source='client.id', read_only=True)
    amount = serializers.DecimalField(
        source='suggested_price_amount', read_only=True, max_digits=20, decimal_places=2,
    )
    interval = serializers.IntegerField(read_only=True)
    interval_from = serializers.DateField(read_only=True, format='%d.%m.%Y')
    interval_to = serializers.DateField(read_only=True, format='%d.%m.%Y')
    tender = TenderSerializerInbank(read_only=True)
    status = serializers.SerializerMethodField('get_status')
    targets = serializers.MultipleChoiceField(choices=Target.CHOICES)
    protocol = serializers.SerializerMethodField('get_protocol')

    def get_protocol(self, request):
        if Target.EXECUTION in request.targets:  # TODO уточнить
            return {
                'protocol_number': request.protocol_number,
                'date': request.protocol_date and request.protocol_date.strftime(
                    '%d.%m.%Y'),
                'lot_number': request.protocol_lot_number
            }
        else:
            return {
                'protocol_number': '',
                'date': '',
                'lot_number': '',
            }

    def get_status(self, request):
        return {
            'status_id': request.status.id,
            'status_description': request.status.name,
            'status_changed': request.status_changed_date.strftime('%d.%m.%Y %H.%M.%S'),
        }

    def get_request_number(self, request):
        if request.request_number:
            return request.request_number
        else:
            return request.id

    class Meta:
        model = Request
        fields = (
            'id',
            'request_number',
            'anketa_id',
            'accounting_report_id',
            'amount',
            'interval',
            'interval_from',
            'interval_to',
            'tender',
            'status',
            'targets',
            'protocol',
        )


class FullRequestSerializerInbank(serializers.ModelSerializer):
    request_number = serializers.SerializerMethodField('get_request_number')
    anketa_id = serializers.IntegerField(source='client.profile.id', read_only=True)
    anketa = ProfileSerializerInbank(source='client.profile', read_only=True)
    accounting_report_id = serializers.IntegerField(source='client.id', read_only=True)
    accounting_report = QuarterSerializerInbank(
        source='client.accounting_report.get_quarters_for_fill',
        many=True, read_only=True
    )
    amount = serializers.DecimalField(
        source='suggested_price_amount', read_only=True, max_digits=20, decimal_places=2,
    )
    interval = serializers.IntegerField(read_only=True)
    interval_from = serializers.DateField(read_only=True, format='%d.%m.%Y')
    interval_to = serializers.DateField(read_only=True, format='%d.%m.%Y')
    tender = TenderSerializerInbank(read_only=True)
    status = serializers.SerializerMethodField('get_status')
    targets = serializers.MultipleChoiceField(choices=Target.CHOICES)
    protocol = serializers.SerializerMethodField('get_protocol')

    def get_protocol(self, request):
        if Target.EXECUTION in request.targets:  # TODO уточнить
            return {
                'protocol_number': request.protocol_number,
                'date': request.protocol_date,
                'lot_number': request.protocol_lot_number
            }
        else:
            return {
                'protocol_number': '',
                'date': '',
                'lot_number': '',
            }

    def get_status(self, request):
        return {
            'status_id': request.status.id,
            'status_description': request.status.name,
            'status_changed': request.status_changed_date.strftime('%d.%m.%Y %H.%M.%S'),
        }

    def get_request_number(self, request):
        if request.request_number:
            return request.request_number
        else:
            return request.id

    class Meta:
        model = Request
        fields = (
            'id',
            'request_number',
            'anketa',
            'anketa_id',
            'accounting_report',
            'accounting_report_id',
            'amount',
            'interval',
            'interval_from',
            'interval_to',
            'tender',
            'status',
            'targets',
            'protocol',
        )


class RequestedCategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    id = serializers.IntegerField()
    created_date = serializers.DateTimeField(format="%d.%m.%Y %H:%M")

    class Meta:
        model = RequestedCategory
        fields = (
            'name',
            'id',
            'created_date',
        )
