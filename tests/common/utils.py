from sqlalchemy import Enum

from app import models

FI_user = {
    "email": "FI_user@noreply.open-contracting.org",
    "name": "Test FI",
    "type": models.UserType.FI.value,
}

FI_user_with_lender = {
    "email": "FI_user_with_lender@noreply.open-contracting.org",
    "name": "Test FI with lender",
    "type": models.UserType.FI.value,
    "lender_id": 1,
}

OCP_user = {
    "email": "OCP_user@noreply.open-contracting.org",
    "name": "OCP_user@example.com",
    "type": models.UserType.OCP.value,
}

application_status_values = tuple(key.value for key in models.ApplicationStatus)
borrower_size_values = tuple(key.value for key in models.BorrowerSize)
credit_type_values = tuple(key.value for key in models.CreditType)
user_type_values = tuple(key.value for key in models.UserType)
borrower_document_type_values = tuple(key.value for key in models.BorrowerDocumentType)


def create_enums(engine):
    existing_enum_types = engine.execute("SELECT typname FROM pg_type WHERE typtype = 'e'").fetchall()

    enum_exists = ("application_status",) in existing_enum_types

    if not enum_exists:
        Enum(*application_status_values, name="application_status", create_type=False)
        engine.execute("CREATE TYPE application_status AS ENUM %s" % str(application_status_values))

    enum_exists = ("borrower_size",) in existing_enum_types

    if not enum_exists:
        Enum(*borrower_size_values, name="borrower_size", create_type=False)
        engine.execute("CREATE TYPE borrower_size AS ENUM %s" % str(borrower_size_values))

    enum_exists = ("credit_type",) in existing_enum_types

    if not enum_exists:
        Enum(*credit_type_values, name="credit_type", create_type=False)
        engine.execute("CREATE TYPE credit_type AS ENUM %s" % str(credit_type_values))

    enum_exists = ("user_type",) in existing_enum_types

    if not enum_exists:
        Enum(*user_type_values, name="user_type", create_type=False)
        engine.execute("CREATE TYPE user_type AS ENUM %s" % str(user_type_values))

    enum_exists = ("borrower_document_type",) in existing_enum_types

    if not enum_exists:
        Enum(*borrower_document_type_values, name="borrower_document_type", create_type=False)
        engine.execute("CREATE TYPE borrower_document_type AS ENUM %s" % str(borrower_document_type_values))
