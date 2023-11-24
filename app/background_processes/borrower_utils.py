from sqlalchemy.orm import Session

from app.schema.core import Borrower, BorrowerStatus

from . import background_utils
from . import colombia_data_access as data_access


def _get_or_create_borrower(entry, session: Session) -> Borrower:
    """
    Get an existing borrower or create a new borrower based on the entry data.

    :param entry: The dictionary containing the borrower data.
    :type entry: dict
    :param session: The database session.
    :type session: Session

    :return: The existing or newly created borrower.
    :rtype: Borrower
    """

    documento_proveedor = data_access.get_documento_proveedor(entry)
    borrower_identifier = background_utils.get_secret_hash(documento_proveedor)
    data = data_access.create_new_borrower(borrower_identifier, documento_proveedor, entry)

    borrower = Borrower.first_by(session, "borrower_identifier", borrower_identifier)
    if borrower:
        if borrower.status == BorrowerStatus.DECLINE_OPPORTUNITIES:
            raise ValueError("Skipping Award - Borrower choosed to not receive any new opportunity")
        return borrower.update(session, **data)

    return Borrower.create(session, **data)
