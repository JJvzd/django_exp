class PrintForm:
    TYPE_HTML = 'html'
    TYPE_DOC = 'doc'
    TYPE_SF_AGREEMENT = 'sf_agreement'
    TYPE_SGB_EXCEL = 'sgb_excel'
    TYPE_INBANK_BG = 'inbank_bg'
    TYPE_INBANK_BG_OFFER = 'inbank_bg_offer'
    TYPE_INBANK_CONCLUSION = 'inbank_conclusion'
    TYPE_SGB_BG = 'sgb_bg'
    TYPE_SGB_ADDITIONAL8 = 'sgb_additional8'
    TYPE_SGB_ADDITIONAL81 = 'sgb_additional81'
    TYPE_METALL_INVEST_ANKETA = 'metall_invest_anketa'
    TYPE_METALL_INVEST_EXCEL = 'metall_invest_excel'
    TYPE_METALL_INVEST_CONCLUSION = 'metall_invest_conclusion'
    TYPE_METALL_INVEST_BENEFICIARS = 'metall_invest_beneficiars'
    TYPE_VORONEJ_EXCEL = 'voronej_excel'
    TYPE_RTBK_ANKETA_EXCEL = 'rtbk_anketa_excel'
    TYPE_RTBK_GUARANTOR_EXCEL = 'rtbk_guarantor_excel'
    TYPE_RIB_TH = 'rib_th'
    TYPE_RIB = 'rib'
    TYPE_MOSCOMBANK_EXECUTION = 'moscombank_execution'
    TYPE_MOSCOMBANK_CONCLUSION = 'moscombank_conclusion'
    TYPE_EAST_EXCEL = 'east_excel'
    TYPE_ZIP = 'zip'
    TYPE_ZIP_BAIKAL = 'zip_baikal'
    TYPE_ZIP_METALL_INVEST = 'zip_metall_invest'
    TYPE_ZIP_RUS_NAR_BANK = 'zip_rus_nar_bank'
    TYPE_EAST_CONCLUSION = 'east_conclusion'
    TYPE_MOSCOMBANK_ANKETA = 'moscombank_anketa'
    TYPE_SPB_CONCLUSION = 'spb_conclusion'
    TYPE_SPB_GUARANTEE = 'spb_guarantee'
    TYPE_SPB_PROFILE = 'spb_profile'
    TYPE_SPB_INDIVIDUAL_RULES = 'spb_individual_rules'
    TYPE_SPB_EXTRADITION_DECISION = 'spb_extradition_decision'
    TYPE_EGRUL = 'egrul'
    TYPE_ABSOLUT_GENERATOR = 'absolut_generator'
    TYPE_ZIP_ABSOLUT = 'zip_absolut'
    TYPE_ZIP_BKS = 'zip_bks'
    TYPE_BKS_GENERATOR = 'bks_generator'
    TYPE_ADAPTERS = (
        (TYPE_DOC,
         'cabinet.base_logic.printing_forms.adapters.doc.'
         'RequestDocBasePrintFormGenerator'
         ),
        (TYPE_HTML,
         'cabinet.base_logic.printing_forms.adapters.html.HTMLPrintFormGenerator'),
        (TYPE_SF_AGREEMENT,
         'cabinet.base_logic.printing_forms.adapters.doc.SFAssigmentPrintForm'),
        (TYPE_SGB_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.SGBExcelPrintForm'),
        (TYPE_INBANK_BG,
         'cabinet.base_logic.printing_forms.adapters.doc.InbankRequestPrintForm'),
        (TYPE_SGB_BG,
         'cabinet.base_logic.printing_forms.adapters.doc.SGBBGExcelPrintForm'),
        (TYPE_SGB_ADDITIONAL8,
         'cabinet.base_logic.printing_forms.adapters.doc.SGBAdditional8ExcelPrintForm'),
        (TYPE_SGB_ADDITIONAL8,
         'cabinet.base_logic.printing_forms.adapters.doc.SGBAdditional8ExcelPrintForm'),
        (TYPE_SGB_ADDITIONAL81,
         'cabinet.base_logic.printing_forms.adapters.doc.SGBAdditional81ExcelPrintForm'),
        (TYPE_METALL_INVEST_ANKETA,
         'cabinet.base_logic.printing_forms.adapters.doc.MetallInvestProfilePrintForm'),
        (TYPE_METALL_INVEST_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.MetallInvestExcelPrintForm'),
        (TYPE_METALL_INVEST_CONCLUSION,
         'cabinet.base_logic.printing_forms.adapters.doc.'
         'MetallInvestConclusionPrintForm'
         ),
        (TYPE_METALL_INVEST_BENEFICIARS,
         'cabinet.base_logic.printing_forms.adapters.doc.'
         'MetallInvestBeneficiarsPrintForm'
         ),
        (TYPE_VORONEJ_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.VoronejExcelPrintForm'),
        (TYPE_RTBK_ANKETA_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.RTBKAnketaExcelPrintForm'),
        (TYPE_RTBK_GUARANTOR_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.RTBKGuarantorExcelPrintForm'),
        (TYPE_RIB_TH, 'cabinet.base_logic.bank_conclusions.rib.RIBConclusionForTH'),
        (TYPE_RIB, 'cabinet.base_logic.printing_forms.adapters.doc.RIBRequestPrintForm'),
        (TYPE_MOSCOMBANK_EXECUTION,
         'cabinet.base_logic.printing_forms.adapters.doc.MosComBankExecutionPrintForm'),
        (TYPE_MOSCOMBANK_CONCLUSION,
         'cabinet.base_logic.printing_forms.adapters.excel.MosComBankConclusion'),
        (TYPE_EAST_EXCEL,
         'cabinet.base_logic.printing_forms.adapters.excel.EastExcelPrintForm'),
        (TYPE_EAST_CONCLUSION,
         'cabinet.base_logic.printing_forms.adapters.doc.EastConclusionPrintForm'),
        (TYPE_MOSCOMBANK_ANKETA,
         'cabinet.base_logic.printing_forms.adapters.download.MoscombankAnketa'),
        (TYPE_INBANK_CONCLUSION,
         'cabinet.base_logic.printing_forms.adapters.excel.InbankConclusion'),
        (TYPE_SPB_GUARANTEE,
         'cabinet.base_logic.printing_forms.adapters.doc.SPBGuaranteePrintForm'),
        (TYPE_SPB_CONCLUSION,
         'cabinet.base_logic.printing_forms.adapters.excel.SPBConclusion'),
        (TYPE_SPB_EXTRADITION_DECISION,
         'cabinet.base_logic.printing_forms.adapters.excel.SPBExtraditionDecision'),
        (TYPE_EGRUL, 'cabinet.base_logic.printing_forms.adapters.download.EgrulAdapter'),
        (TYPE_ABSOLUT_GENERATOR,
         'cabinet.base_logic.printing_forms.adapters.download.AbsolutBankGenerator'),
        (TYPE_ZIP_ABSOLUT,
         'cabinet.base_logic.printing_forms.adapters.zip.ZipAbsolutGenerator'),
        (TYPE_INBANK_BG_OFFER,
         'cabinet.base_logic.printing_forms.adapters.doc.InbankRequestPrintFormOffer'),
        (TYPE_ZIP_BKS,
         'cabinet.base_logic.printing_forms.adapters.zip.ZipBKSGenerator'),
        (TYPE_BKS_GENERATOR,
         'cabinet.base_logic.printing_forms.adapters.download.BKSPrintFormGenerator')
    )
    TYPE_CHOICES = [(x[0], x[0]) for x in TYPE_ADAPTERS]
