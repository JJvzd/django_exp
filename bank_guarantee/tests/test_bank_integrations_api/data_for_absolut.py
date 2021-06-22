DOCUMENTS = {
    'doc_principalCharter': {
        'isMultiple': False,
        'docName': 'Устав принципала'
    },
    'doc_finReportConfirm': {
        'isMultiple': True,
        'docName': 'Подтверждение отправки годовой отчетности'
    },
    'doc_guarantorDocumentEIO': {
        'isMultiple': True,
        'docName': 'Документ, удостоверяющий личность Генерального директора '
                   'или представителя Клиента, действующего по доверенности. '
                   'Обязателен при формировании заявки.'
    },
    'doc_principalPassport': {
        'isMultiple': True,
        'docName': 'Паспорта ФЛ. Обязателен при формировании заявки.'
    },
    'doc_principalDocumentConfirming': {
        'isMultiple': True,
        'docName': 'Документ, подтверждающий право собственности или аренды '
                   'помещения. Обязателен при формировании заявки. '
    },
    'doc_taxForm': {
        'isMultiple': True,
        'docName': 'Налоговая декларация за отчетный период с отметкой о '
                   'принятии или заверенная ЭЦП налоговым органом или копией '
                   'почтовой квитанции. Обязателен при формировании заявки.'},
    'doc_principalLicense': {
        'isMultiple': True, 'docName': 'Лицензии. Обязателен при формировании '
                                       'заявки.'
    },
    'doc_principalExtractRegistry': {
        'isMultiple': False,
        'docName': 'Выписка из реестра акционеров. Обязателен при формировании '
                   'заявки.'
    },
    'doc_finReportQ': {
        'isMultiple': True,
        'docName': 'Бухгалтерская отчетность - бухгалтерский баланс и отчет о '
                   'прибылях и убытках последний квартал. Обязателен при '
                   'формировании заявки.'
    },
    'doc_principalDocumentEIO': {
        'isMultiple': False,
        'docName': 'Документ о назначении единоличного исполнительного органа '
                   'Клиента (протокол/решение об избрании/назначении, приказ о '
                   'назначении). Обязателен при формировании заявки.'
    },
    'doc_principalFinReport': {
        'isMultiple': True,
        'docName': 'Бухгалтерская отчётность. Обязателен при формировании заявки.'
    },
    'doc_agentRelationAgreement': {
        'isMultiple': False,
        'docName': 'Согласие на работу с агентом'
    },
    'doc_declarationBenOwner': {
        'isMultiple': False,
        'docName': 'Декларация бенефициарного владельца'
    },
    'doc_finReportGenerated': {
        'isMultiple': False,
        'docName': 'Бухгалтерская отчетность'
    },
    'doc_limitRequest': {
        'isMultiple': False,
        'docName': 'Заявка на лимит'
    },
    'doc_persDataAgree': {
        'isMultiple': False,
        'docName': 'Согласие на обработку персональных данных'
    },
    'doc_principalForm': {
        'isMultiple': False,
        'docName': 'Анкета клиента'
    },
    'doc_bgRequestLot': {
        'isMultiple': False,
        'docName': 'Заявка на банковскую гарантию'
    },
    'doc_woAppLot': {
        'isMultiple': False,
        'docName': 'Справка об отсутствии необходимости одобрения сделки'
    }
}
STATUS_FOR_SIGN_REQUEST_LIMIT = {
    'orderId': 'test',
    'orderNumber': '004869',
    'taskDefinitionKey': 'UserTaskInitiatorSignDocs',
    'processDefinitionKey': 'bg-pa-limit-check',
    'decisionOptions': [
        {'code': 'SEND_TO_BANK', 'text': 'Отправить в Банк',
         'isCommentRequired': False},
        {'code': 'REJECT',
         'text': 'Отправить заявку в Архив',
         'isCommentRequired': True},
        {'code': 'REWORK', 'text': 'На заполнение заявки',
         'isCommentRequired': False}],
    'bankComment': 'decision.resultCode: Обязательное поле; doc_agentRelationAgreement: Согласовать документ; doc_declarationBenOwner: Согласовать документ; doc_finReportGenerated: Согласовать документ; doc_finReportQ: Согласовать документ; doc_guarantorDocumentEIO: Согласовать документ; doc_limitRequest: Согласовать документ; doc_persDataAgree: Согласовать документ; doc_principalCharter: Согласовать документ; doc_principalDocumentConfirming: Согласовать документ; doc_principalDocumentEIO: Согласовать документ; doc_principalFinReport: Согласовать документ; doc_principalForm: Согласовать документ; doc_taxForm: Согласовать документ',
    'requirements': {'profile': [
        {'path': 'decision.resultCode',
         'title': 'Код решения агента',
         'error': 'Обязательное поле'}], 'documents': [
        {'group': None, 'type': 'doc_agentRelationAgreement',
         'title': 'Согласие на работу с агентом',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_declarationBenOwner',
         'title': 'Декларация бенефициарного владельца',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_finReportGenerated',
         'title': 'Бухгалтерская отчетность',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_finReportQ',
         'title': 'Бухгалтерская отчетность - бухгалтерский баланс и отчет о прибылях и убытках последний квартал.',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_guarantorDocumentEIO',
         'title': 'Документ, удостоверяющий личность Генерального директора или представителя Клиента, действующего по доверенности.',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_limitRequest',
         'title': 'Заявка на лимит',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_persDataAgree',
         'title': 'Согласие на обработку персональных данных',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_principalCharter',
         'title': 'Устав принципала',
         'error': 'Согласовать документ'},
        {'group': None,
         'type': 'doc_principalDocumentConfirming',
         'title': 'Документ, подтверждающий право собственности или аренды помещения.',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_principalDocumentEIO',
         'title': 'Документ о назначении единоличного исполнительного органа Клиента (протокол/решение об избрании/назначении, приказ о назначении).',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_principalFinReport',
         'title': 'Бухгалтерская отчётность.',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_principalForm',
         'title': 'Анкета клиента',
         'error': 'Согласовать документ'},
        {'group': None, 'type': 'doc_taxForm',
         'title': 'Налоговая декларация за отчетный период с отметкой о принятии или заверенная ЭЦП налоговым органом или копией почтовой квитанции.',
         'error': 'Согласовать документ'}],
        'exception': None, 'bank': None},
    'taskName': 'Подписать документы',
    'taskDescription': None, 'url': None,
    'orderStatus': 'PendingAgent',
    'statusDescription': 'Заявка ожидает обновления данных',
    'documents': [
        {'group': None, 'type': 'doc_agentRelationAgreement',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_agentRelationAgreement.docx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b0176478464b600ad'}]},
        {'group': None, 'type': 'doc_declarationBenOwner',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_declarationBenOwner.docx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b017647843e1300a7'}]},
        {'group': None, 'type': 'doc_finReportGenerated',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_finReportGenerated.xlsx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b017647845bf300ab'}]},
        {'group': None, 'type': 'doc_finReportQ',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит_2om4swg.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b0176478405a200a2'},
            {'fileName': '6_бб_2019_квит.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b01764784058d00a1'}]},
        {'group': None, 'type': 'doc_guarantorDocumentEIO',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит_gliCnH7.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b0176478405ea00a5'}]},
        {'group': None, 'type': 'doc_limitRequest',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_limitRequest.docx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b017647844d6900a9'}]},
        {'group': None, 'type': 'doc_persDataAgree',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_dataProcessingAgreement.docx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b0176478453e800aa'}]},
        {'group': None, 'type': 'doc_principalCharter',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит_9yIRidL.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b01764784060400a6'}]},
        {'group': None,
         'type': 'doc_principalDocumentConfirming',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит_zZ4Q4sX.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b0176478405bd00a3'}]},
        {'group': None, 'type': 'doc_principalDocumentEIO',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит_z8DkyVp.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b01764784051e009d'}]},
        {'group': None, 'type': 'doc_principalFinReport',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': '6_бб_2019_квит.pdf',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b01764784057700a0'}]},
        {'group': None, 'type': 'doc_principalForm',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_questionnaire_legalentity.docx',
             'mimeType': None,
             'detachedSignature': None,
             'fileId': '8a8080ea76471c1b01764784459500a8'}]},
        {'group': None, 'type': 'doc_taxForm',
         'comment': 'Согласовать документ',
         'files': [{'fileName': '6_бб_2019_квит_hS6f9XM.pdf',
                    'mimeType': None,
                    'detachedSignature': None,
                    'fileId': '8a8080ea76471c1b0176478404e4009c'}]}]}

LIMIT_CLIENT = [
    {
        "INN": "7726349563",
        "OGRN": "1157746749632",
        "id": "fea9e3d1-8c6f-42d5-b3b3-69c73b85cfb5",
        "externalId": "AXCGqM18GYNEHpg7hCtk",
        "createdDateTime": "2020-02-27T12:56:19.586Z",
        "changedDateTime": "2020-02-27T13:46:30.521Z",
        "totalAmount": 40000000,
        "frozenAmount": 2000000,
        "utilizedAmount": 4999999.99,
        "freeAmount": 33000000.01,
        "endDate": "2020-05-27",
        "constraints": [
            {
                "id": 5021,
                "limitAmount": 40000000,
                "maxOrderAmount": 2000000,
                "startMaxOrderAmount": None,
                "prepaidPercent": None,
                "frozenAmount": 2000000,
                "utilizedAmount": 0,
                "freelimitAmount": 38000000
            },
            {
                "id": 5042,
                "limitAmount": 15000000,
                "maxOrderAmount": 15000000,
                "startMaxOrderAmount": 14500000.50,
                "prepaidPercent": 0.1,
                "frozenAmount": 0,
                "utilizedAmount": 4999999.99,
                "freelimitAmount": 10000000.01
            }
        ]
    }
]

LIMIT_MESSAGE = 'Лимит установлен\nОбщая сумма установленного лимита - 40 000 000,' \
                '0 руб.\nЗаявки на банковскую гарантию на сумму - 2 000 000,' \
                '0 руб. \nДействующие банковские гарантии на сумму - 4 999 999,99 руб. ' \
                '\nСвободный лимит, сумма - 33 000 000,01\nОграничения: \n*\tГарантии с ' \
                'суммой не более 2 000 000,0 руб., без ограничения НМЦ и Аванса могут ' \
                'быть предоствлены на общую сумму не более 40 000 000,0 рублей (' \
                'свободный лимит для ограничения - 38 000 000,0 руб.)\n*\tГарантии без ' \
                'ограничения по сумме гарантии, с ограничением НМЦ не более 14 500 000,' \
                '5 руб. и Аванса не более 10% могут быть предоствлены на общую сумму не ' \
                'более 15 000 000,0 рублей (свободный лимит для ограничения - 10 000 ' \
                '000,01 руб.)'

STATUS_SEND_OFFER = {
    'orderId': 'test', 'orderNumber': '10002348',
    'taskDefinitionKey': 'UserTaskInitiatorApproveDocs2',
    'processDefinitionKey': 'bg-pa-approve-docs', 'decisionOptions': [
        {'code': 'ACCEPT', 'text': 'Отправить на выпуск',
         'isCommentRequired': False},
        {'code': 'REWORK', 'text': 'Отправить в Банк правки',
         'isCommentRequired': True},
        {'code': 'REJECT', 'text': 'Отправить в Архив',
         'isCommentRequired': True},
        {'code': 'APPROVE_PARAMETERS', 'text': 'Изменить параметры',
         'isCommentRequired': False}],
    'bankComment': 'bankGuarantee.guaranteeReceivingWay: Измените способ получения, если необходимо; document: Загрузите документ, если необходимо',
    'requirements': {
        'profile': [
            {
                'path': 'bankGuarantee.guaranteeReceivingWay',
                'title': 'Способ получения. Обязательность и допустимые значения указываются в конфигурации сервиса и приложении к документации',
                'error': 'Измените способ получения, если необходимо'}],
        'documents': [{'group': None, 'type': 'doc_bgRequestLot',
                       'title': 'Заявка на банковскую гарантию',
                       'error': 'Согласовать документ'},
                      {'group': None, 'type': 'doc_woAppLot',
                       'title': 'Справка об отсутствии необходимости одобрения сделки',
                       'error': 'Согласовать документ'},
                      {'group': None, 'type': 'doc_guaranteeLot',
                       'title': 'Макет БГ',
                       'error': 'Согласовать документ'},
                      {'group': None, 'type': 'doc_bill',
                       'title': 'Предложение условий выдачи банковской гарантии и Счет на оплату вознаграждения за выдачу банковской гарантии',
                       'error': 'Согласовать документ'}],
        'exception': None, 'bank': None},
    'taskName': 'Согласовать текст и форму гарантии', 'taskDescription': None,
    'url': None, 'orderStatus': 'PendingAgent',
    'statusDescription': 'Заявка ожидает обновления данных',
    'commission': 36227, 'documents': [
        {'group': None, 'type': 'doc_bgRequestLot',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_request.xlsx', 'mimeType': None,
             'detachedSignature': None,
             'fileId': '82d1ead3-0c89-11eb-aac4-0242ac120035'}]},
        {'group': None, 'type': 'doc_bill', 'comment': 'Согласовать документ',
         'files': [{'fileName': 'bg_bill.docx', 'mimeType': None,
                    'detachedSignature': None,
                    'fileId': '82ee9a95-0c89-11eb-aac4-0242ac120035'}]},
        {'group': None, 'type': 'doc_guaranteeLot',
         'comment': 'Согласовать документ', 'files': [
            {'fileName': 'bg_guarantee_period.docx', 'mimeType': None,
             'detachedSignature': None,
             'fileId': '821662ff-0c89-11eb-aac4-0242ac120035'}]},
        {'group': None, 'type': 'doc_woAppLot', 'comment': 'Согласовать документ',
         'files': [{'fileName': 'bg_woApp.docx', 'mimeType': None,
                    'detachedSignature': None,
                    'fileId': '82c3ba01-0c89-11eb-aac4-0242ac120035'}]}],
}

STATUS_WAIT_PAID = {
    'orderId': 'test',
    'orderNumber': '10002348', 'taskDefinitionKey': 'UserTaskInitiatorPayCommission',
    'processDefinitionKey': 'bg-pa-approve-docs', 'decisionOptions': [
        {'code': 'ACCEPT', 'text': 'Оплачено', 'isCommentRequired': False},
        {'code': 'REJECT', 'text': 'Отправить заявку в Архив', 'isCommentRequired': True},
        {'code': 'APPROVE_LAYOUT', 'text': 'Возврат на согласование макета',
         'isCommentRequired': False}],
    'bankComment': 'bankGuarantee.guaranteeReceivingWay: Измените способ получения, если необходимо; commission: Комиссия не оплачена; decision.resultCode: Обязательное поле',
    'requirements': {'profile': [{'path': 'bankGuarantee.guaranteeReceivingWay',
                                  'title': 'Способ получения. Обязательность и допустимые значения указываются в конфигурации сервиса и приложении к документации',
                                  'error': 'Измените способ получения, если необходимо'},
                                 {'path': 'commission', 'title': 'Информация о комиссии',
                                  'error': 'Комиссия не оплачена'},
                                 {'path': 'decision.resultCode',
                                  'title': 'Код решения агента',
                                  'error': 'Обязательное поле'}], 'documents': [],
                     'exception': None, 'bank': None}, 'taskName': 'Оплатить комиссию',
    'taskDescription': None, 'url': None, 'orderStatus': 'PendingAgent',
    'statusDescription': 'Заявка ожидает обновления данных', 'commission': 36227,
}

STATUS_FINISHED = {
    'orderId': 'test',
    'orderNumber': '10002348', 'decisionOptions': None, 'bankComment': 'Гарантия выдана',
    'requirements': None, 'taskName': None, 'taskDescription': 'Гарантия выдана',
    'url': None, 'orderStatus': 'Executed', 'statusDescription': 'БГ выдана',
    'commission': 36227, 'documents': [
        {'group': None, 'type': 'doc_bgScanLot', 'comment': 'Гарантия во вложении',
         'files': [{'fileName': '2348.pdf', 'mimeType': None, 'detachedSignature': None,
                    'fileId': 'cc9e6025-0c8f-11eb-aac4-0242ac120035'}]}]}
