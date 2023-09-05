from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle

from app.core.settings import app_settings
from app.schema import core

if app_settings.transifex_token and app_settings.transifex_secret:
    from transifex.native import init, tx

    # if more langs added to project add them here
    init(app_settings.transifex_token, ["es", "en"], app_settings.transifex_secret)
    # populate toolkit memory cache with translations from CDS service the first time
    tx.fetch_translations()

pdfmetrics.registerFont(
    TTFont("GTEestiProDisplay", "./fonts/GTEestiProDisplay-Regular.ttf")
)
pdfmetrics.registerFont(
    TTFont("GTEestiProDisplayBd", "./fonts/GTEestiProDisplay-Bold.ttf")
)
pdfmetrics.registerFont(
    TTFont("GTEestiProDisplayIt", "./fonts/GTEestiProDisplay-RegularItalic.ttf")
)
pdfmetrics.registerFont(
    TTFont("GTEestiProDisplayBI", "./fonts/GTEestiProDisplay-BoldItalic.ttf")
)
pdfmetrics.registerFontFamily(
    "GTEestiProDisplay",
    normal="GTEestiProDisplay",
    bold="GTEestiProDisplayBd",
    italic="GTEestiProDisplayIt",
    boldItalic="GTEestiProDisplayBI",
)


# Keep in sync with DOCUMENT_TYPES_NAMES in credere-frontend
document_type_dict = {
    core.BorrowerDocumentType.INCORPORATION_DOCUMENT: "Incorporation Document",
    core.BorrowerDocumentType.SUPPLIER_REGISTRATION_DOCUMENT: "Supplier Registration Document",
    core.BorrowerDocumentType.BANK_NAME: "Bank Name",
    core.BorrowerDocumentType.BANK_CERTIFICATION_DOCUMENT: "Bank Certification Document",
    core.BorrowerDocumentType.FINANCIAL_STATEMENT: "Financial Statement",
    core.BorrowerDocumentType.SIGNED_CONTRACT: "Signed Contract",
    core.BorrowerDocumentType.COMPLIANCE_REPORT: "Compliance Report",
    core.BorrowerDocumentType.SHAREHOLDER_COMPOSITION: "Shareholder composition",
    core.BorrowerDocumentType.CHAMBER_OF_COMMERCE: "Chamber of Commerce",
    core.BorrowerDocumentType.THREE_LAST_BANK_STATEMENT: "Three last bank statement",
}

# Keep in sync with MSME_TYPES_NAMES in credere-frontend
borrower_size_dict = {
    core.BorrowerSize.NOT_INFORMED: "Not informed",
    core.BorrowerSize.MICRO: "0 to 10",
    core.BorrowerSize.SMALL: "11 to 50",
    core.BorrowerSize.MEDIUM: "51 to 200",
}

# Keep in sync with SECTOR_TYPES in credere-frontend
sector_dict = {
    "agricultura": "Agricultura, ganadería, caza, silvicultura y pesca",
    "minas": "Explotación de minas y canteras",
    "manufactura": "Industrias manufactureras",
    "electricidad": "Suministro de electricidad, gas, vapor y aire acondicionado",
    "agua": "Distribución de agua; evacuación y tratamiento de aguas residuales, gestión de desechos y actividades de "
            "saneamiento ambiental",
    "construccion": "Construcción",
    "Transporte y almacenamiento": "Transporte",
    "alojamiento": "Alojamiento y servicios de comida",
    "comunicaciones": "Información y comunicaciones",
    "actividades_financieras": "Actividades financieras y de seguros",
    "actividades_inmobiliarias": "Actividades inmobiliarias",
    "actividades_profesionales": "Actividades profesionales, científicas y técnicas",
    "actividades_servicios_administrativos": "Actividades de servicios administrativos y de apoyo",
    "administracion_publica": "Administración pública y defensa; planes de seguridad social de afiliación obligatoria",
    "educacion": "Educación",
    "atencion_salud": "Actividades de atención de la salud humana y de asistencia social",
    "actividades_artisticas": "Actividades artísticas, de entretenimiento y recreación",
    "otras_actividades": "Otras actividades de servicios",
    "actividades_hogares": "Actividades de los hogares individuales en calidad de empleadores; actividades no "
                           "diferenciadas de los hogares individuales como productores de bienes yservicios para uso "
                           "propio",
    "actividades_organizaciones_extraterritoriales": "Actividades de organizaciones y entidades extraterritoriales'",
}

width, height = A4
styles = getSampleStyleSheet()
styleN = styles["BodyText"]
styleN.fontName = "GTEestiProDisplay"
styleN.alignment = TA_LEFT
styleBH = styles["Normal"]
styleBH.fontName = "GTEestiProDisplay"
styleBH.alignment = TA_CENTER

styleTitle = styles["Title"]
styleTitle.fontName = "GTEestiProDisplay"

styleSubTitle = styles["Heading2"]
styleSubTitle.fontName = "GTEestiProDisplay"


def get_translated_string(key, lang, params=None) -> str:
    from transifex.native import tx

    translation = tx.translate(key, lang, params=params)
    return translation


def create_table(data):
    table = Table(data, colWidths=[250, 350])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "#D6E100"),
                ("TEXTCOLOR", (0, 0), (-1, 0), "#444444"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "GTEestiProDisplay"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), "#F2F2F2"),
                ("FONTNAME", (0, 0), (-1, -1), "GTEestiProDisplay"),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("WORDWRAP", (0, 0), (-1, -1)),
            ]
        )
    )

    return table
