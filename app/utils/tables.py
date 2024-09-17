import locale
from datetime import datetime
from decimal import Decimal

from reportlab.platypus import Paragraph, Table

from app import models
from app.i18n import _
from reportlab_mods import create_table, styleN


def _format_currency(number: Decimal | None, currency: str) -> str:
    if number is None:
        return "-"
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
    Create a table of application information.

    :param application: The application's data.
    :param lang: The lang requested.
    :return: The generated table.
    """
    data = [
        [
            _("Financing Options", lang),
            _("Data", lang),
        ],
        [
            _("Lender", lang),
            application.lender.name,
        ],
        [
            _("Amount requested", lang),
            _format_currency(application.amount_requested, application.currency),
        ],
    ]

    if application.credit_product.type == models.CreditType.LOAN:
        data.append(
            [
                _("Type", lang),
                _("Loan", lang),
            ],
        )
        data.append(
            [
                _("Payment start date", lang),
                _format_date(str(application.payment_start_date)),
            ],
        )
        data.append(
            [
                _("Repayment terms", lang),
                _(
                    "%(repayment_years)s year(s), %(repayment_months)s month(s)",
                    lang,
                    repayment_years=application.repayment_years,
                    repayment_months=application.repayment_months,
                ),
            ],
        )
    else:
        data.append(
            [
                _("Type", lang),
                _("Credit Line", lang),
            ],
        )

    if application.status == models.ApplicationStatus.COMPLETED:
        data.append(
            [
                _("Contract amount", lang),
                _format_currency(application.contract_amount_submitted, application.currency),
            ]
        )
        data.append(
            [
                _("Credit amount", lang),
                _format_currency(application.disbursed_final_amount, application.currency),
            ]
        )

    return create_table(data)


def create_award_table(award: models.Award, lang: str) -> Table:
    """
    Create a table of Open Contracting award data.

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

    return create_table(
        [
            [
                _("Award Data", lang),
                _("Data", lang),
            ],
            [
                _("View data in SECOP II", lang),
                Paragraph(f'<link href="{award.source_url}">{award.source_url}</link>', styleN),
            ],
            [
                _("Award Title", lang),
                Paragraph(award.title, styleN),
            ],
            [
                _("Contracting Process ID", lang),
                Paragraph(award.contracting_process_id, styleN),
            ],
            [
                _("Award Description", lang),
                Paragraph(award.description, styleN),
            ],
            [
                _("Award Date", lang),
                _format_date(str(award.award_date)),
            ],
            [
                _("Award Value Currency & Amount", lang),
                _format_currency(award.award_amount, award.award_currency),
            ],
            [
                _("Contract Start Date", lang),
                _format_date(str(award.contractperiod_startdate)),
            ],
            [
                _("Contract End Date", lang),
                _format_date(str(award.contractperiod_enddate)),
            ],
            [
                _("Payment Method", lang),
                payment_method_text,
            ],
            [
                _("Buyer Name", lang),
                Paragraph(
                    award.buyer_name,
                    styleN,
                ),
            ],
            [
                _("Procurement Method", lang),
                Paragraph(award.procurement_method, styleN),
            ],
            [
                _("Contract Type", lang),
                Paragraph(award.procurement_category, styleN),
            ],
        ]
    )


def create_borrower_table(borrower: models.Borrower, application: models.Application, lang: str) -> Table:
    """
    Create a table of borrower data.

    :param borrower: The borrower's data.
    :param lang: The lang requested.
    :return: The generated table.
    """
    return create_table(
        [
            [
                _("MSME Data", lang),
                _("Data", lang),
            ],
            [
                _("Legal Name", lang),
                Paragraph(borrower.legal_name, styleN),
            ],
            [
                _("Address", lang),
                Paragraph(borrower.address, styleN),
            ],
            [
                _("National Tax ID", lang),
                borrower.legal_identifier,
            ],
            [
                _("Registration Type", lang),
                borrower.type,
            ],
            [
                _("Size", lang),
                _(borrower.size, lang),
            ],
            [
                _("Sector", lang),
                _(borrower.sector, lang),
            ],
            [
                _("Annual Revenue", lang),
                _format_currency(borrower.annual_revenue, borrower.currency),
            ],
            [
                _("Business Email", lang),
                application.primary_email,
            ],
        ]
    )


def create_documents_table(documents: list[models.BorrowerDocument], lang: str) -> Table:
    """
    Create a table of borrower information and documents.

    :param documents: List of documents.
    :param lang: The lang requested.
    :return: The generated table.
    """
    data = [[_("MSME Documents", lang), _("Data", lang)]]
    data.extend([_(document.type), document.name] for document in documents)

    return create_table(data)
