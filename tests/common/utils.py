from sqlalchemy import Enum

from app.schema import core

FI_user = {
    "email": "FI_user@example.com",
    "name": "Test FI",
    "type": core.UserType.FI.value,
}

OCP_user = {
    "email": "OCP_user@example.com",
    "name": "OCP_user@example.com",
    "type": core.UserType.OCP.value,
}

application_status_values = tuple(key.value for key in core.ApplicationStatus)
borrower_size_values = tuple(key.value for key in core.BorrowerSize)
credit_type_values = tuple(key.value for key in core.CreditType)
user_type_values = tuple(key.value for key in core.UserType)
borrower_document_type_values = tuple(key.value for key in core.BorrowerDocumentType)


def create_enums(engine):
    existing_enum_types = engine.execute(
        "SELECT typname FROM pg_type WHERE typtype = 'e'"
    ).fetchall()

    enum_exists = ("application_status",) in existing_enum_types

    if not enum_exists:
        Enum(*application_status_values, name="application_status", create_type=False)
        engine.execute(
            "CREATE TYPE application_status AS ENUM %s" % str(application_status_values)
        )

    enum_exists = ("borrower_size",) in existing_enum_types

    if not enum_exists:
        Enum(*borrower_size_values, name="borrower_size", create_type=False)
        engine.execute(
            "CREATE TYPE borrower_size AS ENUM %s" % str(borrower_size_values)
        )

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
        Enum(
            *borrower_document_type_values,
            name="borrower_document_type",
            create_type=False
        )
        engine.execute(
            "CREATE TYPE borrower_document_type AS ENUM %s"
            % str(borrower_document_type_values)
        )
