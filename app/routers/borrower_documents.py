from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import app.utils.applications as utils
from app import dependencies, models
from app.db import get_db, transaction_session

router = APIRouter()


@router.post(
    "/applications/upload-document",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_document(
    file: UploadFile,
    uuid: str = Form(...),
    type: str = Form(...),
    session: Session = Depends(get_db),
):
    """
    Upload a document for an application.

    :param file: The uploaded file.
    :type file: UploadFile

    :param uuid: The UUID of the application.
    :type uuid: str

    :param type: The type of the document.
    :type type: str

    :param session: The database session.
    :type session: Session

    :return: The created or updated borrower document.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)
        if not application.pending_documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload document at this stage",
            )

        document = utils.create_or_update_borrower_document(filename, application, type, session, new_file)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            data={"file_name": filename},
            application_id=application.id,
        )

        return document


@router.post(
    "/applications/upload-contract",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_contract(
    file: UploadFile,
    uuid: str = Form(...),
    session: Session = Depends(get_db),
):
    """
    Upload a contract document for an application.

    :param file: The uploaded file.
    :type file: UploadFile

    :param uuid: The UUID of the application.
    :type uuid: str

    :param session: The database session.
    :type session: Session

    :return: The created or updated borrower document representing the contract.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_uuid(uuid, session)

        utils.check_application_status(application, models.ApplicationStatus.APPROVED)

        document = utils.create_or_update_borrower_document(
            filename,
            application,
            models.BorrowerDocumentType.SIGNED_CONTRACT,
            session,
            new_file,
        )

        return document


@router.post(
    "/applications/{id}/upload-compliance",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_compliance(
    id: int,
    file: UploadFile,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
):
    """
    Upload a compliance document for an application.

    :param id: The ID of the application.
    :type id: int

    :param file: The uploaded file.
    :type file: UploadFile

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The created or updated borrower document representing the compliance report.
    :rtype: models.BorrowerDocumentBase

    """
    with transaction_session(session):
        new_file, filename = utils.validate_file(file)
        application = utils.get_application_by_id(id, session)

        utils.check_FI_user_permission(application, user)

        document = utils.create_or_update_borrower_document(
            filename,
            application,
            models.BorrowerDocumentType.COMPLIANCE_REPORT,
            session,
            new_file,
            True,
        )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.FI_UPLOAD_COMPLIANCE,
            data={"file_name": filename},
            application_id=application.id,
        )

        return document
