from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from app.db.session import get_db
from app.schema.core import Award

from . import background_utils
from . import colombia_data_access as data_access


def get_existing_award(source_contract_id: str, session: Session):
    award = (
        session.query(Award)
        .filter(Award.source_contract_id == source_contract_id)
        .first()
    )

    return award


def get_last_updated_award_date():
    with contextmanager(get_db)() as session:
        award = (
            session.query(Award).order_by(desc(Award.source_last_updated_at)).first()
        )

        if not award:
            return None

        return award.source_last_updated_at


def insert_award(award: Award, session: Session):
    obj_db = Award(**award)
    obj_db.created_at = datetime.utcnow()
    obj_db.missing_data = background_utils.get_missing_data_keys(award)

    session.add(obj_db)
    session.flush()
    return obj_db


def create_new_award(
    source_contract_id: str,
    entry: dict,
    borrower_id: int = None,
    previous: bool = False,
) -> dict:
    return data_access.create_new_award(
        source_contract_id, entry, borrower_id, previous
    )


def get_new_contracts(index: int, last_updated_award_date):
    return data_access.get_new_contracts(index, last_updated_award_date)


def get_previous_contracts(documento_proveedor):
    return data_access.get_previous_contracts(documento_proveedor)


def get_source_contract_id(entry):
    return data_access.get_source_contract_id(entry)


def create_award(entry, session: Session, borrower_id=None, previous=False) -> Award:
    source_contract_id = get_source_contract_id(entry)

    # if award already exists
    if get_existing_award(source_contract_id, session):
        background_utils.raise_sentry_error(
            f"Skipping Award [previous {previous}] - Already exists on database", entry
        )

    new_award = create_new_award(source_contract_id, entry, borrower_id, previous)

    award = insert_award(new_award, session)
    return award
