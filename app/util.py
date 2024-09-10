import base64
import hashlib
import hmac
import os.path
import uuid
from contextlib import contextmanager
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Callable, Generator, TypeVar

import httpx
import orjson
from email_validator import EmailNotValidError, validate_email
from fastapi import File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlmodel import col

from app import models
from app.db import get_db, handle_skipped_award
from app.exceptions import SkippedAwardError
from app.i18n import _
from app.settings import app_settings
from app.sources import colombia as data_access

T = TypeVar("T")
MAX_FILE_SIZE = app_settings.max_file_size_mb * 1024 * 1024  # MB in bytes
ALLOWED_EXTENSIONS = {".png", ".pdf", ".jpeg", ".jpg", ".zip"}


# https://fastapi.tiangolo.com/tutorial/path-operation-configuration/#tags-with-enums
class Tags(Enum):
    applications = "applications"
    lenders = "lenders"
    meta = "meta"
    statistics = "statistics"
    users = "users"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


# In future, httpx.Client might allow custom decoders. https://github.com/encode/httpx/issues/717
def loads(response: httpx.Response) -> Any:
    return orjson.loads(response.text)


def get_object_or_404(session: Session, model: type[T], field: str, value: Any) -> T:
    obj = model.first_by(session, field, value)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_("%(model_name)s not found", model_name=model.__name__),
        )
    return obj


def generate_uuid(string: str) -> str:
    """
    Generate a UUID based on the given string.

    :param string: The input string to generate the UUID from.
    :return: The generated UUID.
    """

    return str(uuid.uuid5(uuid.NAMESPACE_DNS, string))


def get_secret_hash(string: str) -> str:
    """
    Calculate the hash of a string.
    """

    message = string.encode()
    key = app_settings.hash_key.encode()
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()


def is_valid_email(email: str) -> bool:
    """
    Check if the given email is valid.

    :param email: The email address to validate.
    :return: True if the email is valid, False otherwise.
    """
    try:
        return bool(validate_email(email, allow_smtputf8=False))
    except EmailNotValidError:
        return False


def validate_file(file: UploadFile = File(...)) -> tuple[bytes, str | None]:
    """
    Validates the uploaded file.

    This function checks whether the file has an allowed format and whether its size is below the maximum allowed size.

    If the file does not pass these checks, raise an HTTPException. Otherwise, return the file and its filename.

    :param file: The uploaded file.
    :return: A dictionary mapping the file to its filename.
    :raise HTTPException: If the file format is not allowed or if the file size is too large.
    """
    filename = file.filename
    if os.path.splitext(filename)[1].lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_("Format not allowed. It must be a PNG, JPEG, PDF or ZIP file"),
        )
    new_file = file.file.read()
    if len(new_file) >= MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=_("File is too large"),
        )
    return new_file, filename


def get_modified_data_fields(session: Session, application: models.Application) -> models.ApplicationWithRelations:
    modified_data_fields: dict[str, Any] = {"award_updates": {}, "borrower_updates": {}}

    for action in (
        session.query(models.ApplicationAction)
        .join(models.Application)
        .filter(
            models.ApplicationAction.application_id == application.id,
            col(models.ApplicationAction.type).in_(
                [models.ApplicationActionType.AWARD_UPDATE, models.ApplicationActionType.BORROWER_UPDATE]
            ),
        )
    ):
        action_data = action.data
        key_prefix = (
            "award_updates" if action.type == models.ApplicationActionType.AWARD_UPDATE else "borrower_updates"
        )
        for key, value in action_data.items():
            if (
                key not in modified_data_fields[key_prefix]
                or action.created_at > modified_data_fields[key_prefix][key]["modified_at"]
            ):
                modified_data_fields[key_prefix][key] = {
                    "modified_at": action.created_at,
                    "user": action.user.name,
                    "user_type": action.user.type,
                }

    return models.ApplicationWithRelations(
        **application.model_dump(),
        award=application.award,
        borrower=application.borrower,
        lender=application.lender,
        credit_product=application.credit_product,
        borrower_documents=application.borrower_documents,
        modified_data_fields=modified_data_fields,
    )


def create_award_from_data_source(
    session: Session, entry: dict[str, Any], borrower_id: int | None = None, *, previous: bool = False
) -> models.Award:
    """
    Create a new award and insert it into the database.

    :param entry: The dictionary containing the award data.
    :param borrower_id: The ID of the borrower associated with the award. (default: None)
    :param previous: Whether the award is a previous award or not. (default: False)
    :return: The inserted award.
    """

    data = data_access.get_award(entry, borrower_id, previous)
    if award := models.Award.first_by(session, "source_contract_id", data["source_contract_id"]):
        raise SkippedAwardError(
            "Award already exists",
            data={
                "found": award.id,
                "lookup": {"source_contract_id": data["source_contract_id"]},
                "create": {"entry": entry, "borrower_id": borrower_id, "previous": previous},
            },
        )

    return models.Award.create(session, **data)


# A background task.
def get_previous_awards_from_data_source(
    borrower_id: int, db_provider: Callable[[], Generator[Session, None, None]] = get_db
) -> None:
    """
    Fetch previous awards for a borrower that accepted an application. This won't generate an application,
    it will just insert the awards in our database

    :param borrower_id: The ID of the borrower for whom to fetch and process previous awards.
    """
    with contextmanager(db_provider)() as session:
        borrower = models.Borrower.get(session, borrower_id)

    awards_response_json = loads(data_access.get_previous_awards(borrower.legal_identifier))
    if not awards_response_json:
        return

    for entry in awards_response_json:
        with contextmanager(db_provider)() as session:
            with handle_skipped_award(session, "Error creating award"):
                create_award_from_data_source(session, entry, borrower.id, previous=True)

                session.commit()


def create_or_update_borrower_document(
    session: Session,
    filename: str | None,
    application: models.Application,
    type: models.BorrowerDocumentType,
    file: bytes,
    *,
    verified: bool | None = False,
) -> models.BorrowerDocument:
    """
    Creates a new borrower document or updates an existing one.

    This function first checks if a document of the same type already exists for the application in the session.
    If it does, it updates the existing document's file, name, verified status, and submission time with the provided
    values. If it doesn't, it creates a new BorrowerDocument with the provided values and adds it to the session.

    :param filename: The name of the file to be added or updated.
    :param application: The application associated with the document.
    :param type: The type of the document.
    :param file: The file to be added or updated.
    :param verified: The verified status of the document. Defaults to False.
    :return: The newly created or updated BorrowerDocument.
    """

    existing_document = (
        session.query(models.BorrowerDocument)
        .filter(
            models.BorrowerDocument.application_id == application.id,
            models.BorrowerDocument.type == type,
        )
        .first()
    )

    if existing_document:
        return existing_document.update(
            session,
            file=file,
            name=filename,
            verified=verified,
            submitted_at=datetime.utcnow(),
        )
    else:
        return models.BorrowerDocument.create(
            session,
            application_id=application.id,
            type=type,
            file=file,
            name=filename,
            verified=verified,
        )
