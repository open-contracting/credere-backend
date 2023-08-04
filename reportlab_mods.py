from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle

from app.schema import core

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
    core.BorrowerSize.MICRO: "Micro",
    core.BorrowerSize.SMALL: "Small",
    core.BorrowerSize.MEDIUM: "Medium",
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
styleN.alignment = TA_LEFT
styleBH = styles["Normal"]
styleBH.alignment = TA_CENTER


def create_table(data):
    table = Table(data, colWidths=[250, 350])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), "#F8F9FA"),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("WORDWRAP", (0, 0), (-1, -1)),
            ]
        )
    )

    return table
