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


document_type_dict = {
    core.BorrowerDocumentType.INCORPORATION_DOCUMENT: "Incorporation Document",
    core.BorrowerDocumentType.SUPPLIER_REGISTRATION_DOCUMENT: "Supplier Registration Document",
    core.BorrowerDocumentType.BANK_NAME: "Bank Name",
    core.BorrowerDocumentType.BANK_CERTIFICATION_DOCUMENT: "Bank Certification Document",
    core.BorrowerDocumentType.FINANCIAL_STATEMENT: "Financial Statement",
    core.BorrowerDocumentType.SIGNED_CONTRACT: "Signed Contract",
    core.BorrowerDocumentType.COMPLIANCE_REPORT: "Compliance Report",
}

borrower_size_dict = {
    core.BorrowerSize.NOT_INFORMED: "Not informed",
    core.BorrowerSize.MICRO: "0 to 10",
    core.BorrowerSize.SMALL: "11 to 50",
    core.BorrowerSize.MEDIUM: "51 to 200",
}

sector_dict = {
    "accommodation_and_food_services": "Accommodation and Food Services",
    "administration": "Administration",
    "agriculture_forestry_fishing_and_hunting": "Agriculture, Forestry, Fishing and Hunting",
    "arts_entertainment_and_recreation": "Arts, Entertainment and Recreation",
    "construction": "Construction",
    "educational_services": "Educational Services",
    "finance_and_insurance": "Finance and Insurance",
    "healthcare_and_social_assistance": "Healthcare and Social Assistance",
    "information": "Information",
    "manufacturing": "Manufacturing",
    "mining": "Mining",
    "other_services": "Other Services",
    "professional_scientific_and_technical_services": "Professional, Scientific and Technical Services",
    "real_estate_and_rental_and_leasing": "Real Estate and Rental and Leasing",
    "retail_trade": "Retail Trade",
    "transportation_and_warehousing": "Transportation and Warehousing",
    "utilities": "Utilities",
    "wholesale_trade": "Wholesale Trade",
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
