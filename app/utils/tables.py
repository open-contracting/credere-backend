import locale
from datetime import datetime
from decimal import Decimal

from reportlab.platypus import Paragraph, Table

from app import models
from app.i18n import get_translated_string
from reportlab_mods import borrower_size_dict, create_table, document_type_dict, sector_dict, styleN


def _format_currency(number: Decimal | None, currency: str) -> str:
    if isinstance(number, str):
        try:
            number = int(number)
        except ValueError:
            return "-"

    locale.setlocale(locale.LC_ALL, "")
    formatted_number = locale.format_string("%d", number, grouping=True)
    return f"{currency}$ {formatted_number}"


def _format_date(date_str: str) -> str:
    if date_str == "None":
        return "-"
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")


def create_application_table(application: models.Application, lang: str) -> Table:
    """
    Creates a table of application information.

    :param application: The application's data.
    :param lang: The lang requested.
    :return: The generated table.
    """

    data = [
        [
            get_translated_string("Financing Options", lang),
            get_translated_string("Data", lang),
        ],
        [
            get_translated_string("Lender", lang),
            application.lender.name,
        ],
        [
            get_translated_string("Amount requested", lang),
            _format_currency(application.amount_requested, application.currency),
        ],
    ]

    if application.credit_product.type == models.CreditType.LOAN:
        data.append(
            [
                get_translated_string("Type", lang),
                get_translated_string("Loan", lang),
            ],
        )
        data.append(
            [
                get_translated_string("Payment start date", lang),
                _format_date(str(application.payment_start_date)),
            ],
        )
        data.append(
            [
                get_translated_string("Repayment terms", lang),
                get_translated_string(
                    "{repayment_years} year(s), {repayment_months} month(s)",
                    lang,
                    {
                        "repayment_years": application.repayment_years,
                        "repayment_months": application.repayment_months,
                    },
                ),
            ],
        )
    else:
        data.append(
            [
                get_translated_string("Type", lang),
                get_translated_string("Credit Line", lang),
            ],
        )

    if application.status == models.ApplicationStatus.COMPLETED:
        data.append(
            [
                get_translated_string("Contract amount", lang),
                _format_currency(application.contract_amount_submitted, application.currency),
            ]
        )
        data.append(
            [
                get_translated_string("Credit amount", lang),
                _format_currency(application.disbursed_final_amount, application.currency),
            ]
        )
    return create_table(data)


def create_award_table(award: models.Award, lang: str) -> Table:
    """
    Creates a table of Open Contracting award data.

    :param award: The award data.
    :param lang: The lang requested.
    :return: The generated table.
    """

    payment_method_text = f"""Habilita Pago Adelantado: {
        _format_currency(award.payment_method.get("habilita_pago_adelantado", ""), award.award_currency)
    }\nValor De Pago Adelantado: {
        _format_currency(award.payment_method.get("valor_de_pago_adelantado", ""), award.award_currency)
    }\nValor Facturado: {
        _format_currency(award.payment_method.get("valor_facturado", ""), award.award_currency)
    }\nValor Pendiente De Pago: {
        _format_currency(award.payment_method.get("valor_pendiente_de_pago", ""), award.award_currency)
    }\nValor Pagado: {
        _format_currency(award.payment_method.get("valor_pagado", ""), award.award_currency)
    }\n"""
    secop_link = f"""<link href="{award.source_url}">{award.source_url}</link>"""

    data = [
        [
            get_translated_string("Award Data", lang),
            get_translated_string("Data", lang),
        ],
        [
            get_translated_string("View data in SECOP II", lang),
            Paragraph(secop_link, styleN),
        ],
        [
            get_translated_string("Award Title", lang),
            Paragraph(award.title, styleN),
        ],
        [
            get_translated_string("Contracting Process ID", lang),
            Paragraph(award.contracting_process_id, styleN),
        ],
        [
            get_translated_string("Award Description", lang),
            Paragraph(award.description, styleN),
        ],
        [
            get_translated_string("Award Date", lang),
            _format_date(str(award.award_date)),
        ],
        [
            get_translated_string("Award Value Currency & Amount", lang),
            _format_currency(award.award_amount, award.award_currency),
        ],
        [
            get_translated_string("Contract Start Date", lang),
            _format_date(str(award.contractperiod_startdate)),
        ],
        [
            get_translated_string("Contract End Date", lang),
            _format_date(str(award.contractperiod_enddate)),
        ],
        [
            get_translated_string("Payment Method", lang),
            payment_method_text,
        ],
        [
            get_translated_string("Buyer Name", lang),
            Paragraph(
                award.buyer_name,
                styleN,
            ),
        ],
        [
            get_translated_string("Procurement Method", lang),
            Paragraph(award.procurement_method, styleN),
        ],
        [
            get_translated_string("Contract Type", lang),
            Paragraph(award.procurement_category, styleN),
        ],
    ]

    return create_table(data)


def create_borrower_table(borrower: models.Borrower, application: models.Application, lang: str) -> Table:
    """
    Creates a table of borrower data.

    :param borrower: The borrower's data.
    :param lang: The lang requested.
    :return: The generated table.
    """

    data = [
        [
            get_translated_string("MSME Data", lang),
            get_translated_string("Data", lang),
        ],
        [
            get_translated_string("Legal Name", lang),
            Paragraph(borrower.legal_name, styleN),
        ],
        [
            get_translated_string("Address", lang),
            Paragraph(borrower.address, styleN),
        ],
        [
            get_translated_string("National Tax ID", lang),
            borrower.legal_identifier,
        ],
        [
            get_translated_string("Registration Type", lang),
            borrower.type,
        ],
        [
            get_translated_string("Size", lang),
            get_translated_string(borrower_size_dict[borrower.size], lang),
        ],
        [
            get_translated_string("Sector", lang),
            get_translated_string(sector_dict[borrower.sector], lang),
        ],
        [
            get_translated_string("Annual Revenue", lang),
            _format_currency(borrower.annual_revenue, borrower.currency),
        ],
        [
            get_translated_string("Business Email", lang),
            application.primary_email,
        ],
    ]
    return create_table(data)


def create_documents_table(documents: list[models.BorrowerDocument], lang: str) -> Table:
    """
    Creates a table of borrower information and documents.

    :param documents: List of documents.
    :param lang: The lang requested.
    :return: The generated table.
    """

    data = [
        [
            get_translated_string("MSME Documents", lang),
            get_translated_string("Data", lang),
        ]
    ]
    for document in documents:
        data.append(
            [
                get_translated_string(document_type_dict[document.type], lang),
                document.name,
            ]
        )

    return create_table(data)
