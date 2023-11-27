import logging
from datetime import datetime
from typing import List

from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, parsers, serializers, util
from app.aws import CognitoClient
from app.db import get_db, transaction_session
from app.utils.statistics import update_statistics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/applications/{id}/reject-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def reject_application(
    payload: parsers.LenderRejectedApplication,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(roles=(models.UserType.FI,))
    ),
):
    """
    Reject an application:
    Changes the status from "STARTED" to "REJECTED".

    :param payload: The rejected application data.
    :type payload: parsers.LenderRejectedApplication

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The rejected application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        if application.status not in (
            models.ApplicationStatus.CONTRACT_UPLOADED,
            models.ApplicationStatus.STARTED,
        ):
            message = "Application status is not {} or {}".format(
                models.ApplicationStatus.STARTED.name,
                models.ApplicationStatus.CONTRACT_UPLOADED.name,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            )

        payload_dict = jsonable_encoder(payload, exclude_unset=True)
        application.stage_as_rejected(payload_dict)
        # This next call performs the `session.flush()`.
        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.REJECTED_APPLICATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )
        options = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                models.CreditProduct.borrower_size == application.borrower.size,
                models.CreditProduct.lender_id != application.lender_id,
                models.CreditProduct.lower_limit <= application.amount_requested,
                models.CreditProduct.upper_limit >= application.amount_requested,
            )
            .all()
        )
        message_id = client.send_rejected_email_to_sme(application, options)
        models.Message.create(
            session,
            application=application,
            type=models.MessageType.REJECTED_APPLICATION,
            external_message_id=message_id,
        )
        background_tasks.add_task(update_statistics)
        return application


@router.post(
    "/applications/{id}/complete-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def complete_application(
    payload: parsers.LenderReviewContract,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.CONTRACT_UPLOADED,),
        )
    ),
):
    """
    Complete an application:
    Changes application status from "CONTRACT_UPLOADED" to "COMPLETED".

    :param payload: The completed application data.
    :type payload: parsers.LenderReviewContract

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The completed application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        application.stage_as_completed(payload.disbursed_final_amount)
        application.completed_in_days = application.days_waiting_for_lender(session)
        # This next call performs the `session.flush()`.
        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.FI_COMPLETE_APPLICATION,
            # payload.disbursed_final_amount is a Decimal.
            data=jsonable_encoder({"disbursed_final_amount": payload.disbursed_final_amount}),
            application_id=application.id,
            user_id=user.id,
        )

        message_id = client.send_application_credit_disbursed(application)
        models.Message.create(
            session,
            application=application,
            type=models.MessageType.CREDIT_DISBURSED,
            external_message_id=message_id,
        )
        background_tasks.add_task(update_statistics)
        return application


@router.post(
    "/applications/{id}/approve-application",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def approve_application(
    payload: parsers.LenderApprovedData,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.STARTED,),
        )
    ),
):
    """
    Approve an application:
    Changes application status from "STARTED" to "APPROVED".

    Sends an email to  SME notifying the current stage of their application.

    :param payload: The approved application data.
    :type payload: parsers.LenderApprovedData

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The approved application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        # Check if all keys present in an instance of UpdateDataField exist and have truthy values in
        # the application's `secop_data_verification`.
        not_validated_fields = []
        app_secop_dict = application.secop_data_verification.copy()
        fields = list(parsers.UpdateDataField().dict().keys())
        for key in fields:
            if key not in app_secop_dict or not app_secop_dict[key]:
                not_validated_fields.append(key)
        if not_validated_fields:
            logger.error(f"Following fields were not validated: {not_validated_fields}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=util.ERROR_CODES.BORROWER_FIELD_VERIFICATION_MISSING.value,
            )

        # Check all documents are verified.
        not_validated_documents = []
        for document in application.borrower_documents:
            if not document.verified:
                not_validated_documents.append(document.type.name)
        if not_validated_documents:
            logger.error(f"Following documents were not validated: {not_validated_documents}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=util.ERROR_CODES.DOCUMENT_VERIFICATION_MISSING.value,
            )

        # Approve the application.
        payload_dict = jsonable_encoder(payload, exclude_unset=True)
        application.lender_approved_data = payload_dict
        application.status = models.ApplicationStatus.APPROVED
        current_time = datetime.now(application.created_at.tzinfo)
        application.lender_approved_at = current_time

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPROVED_APPLICATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )

        message_id = client.send_application_approved_to_sme(application)
        models.Message.create(
            session,
            application=application,
            type=models.MessageType.APPROVED_APPLICATION,
            external_message_id=message_id,
        )
        background_tasks.add_task(update_statistics)
        return application


@router.put(
    "/applications/{id}/verify-data-field",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def verify_data_field(
    payload: parsers.UpdateDataField,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.FI,),
            statuses=(
                models.ApplicationStatus.STARTED,
                models.ApplicationStatus.INFORMATION_REQUESTED,
            ),
        )
    ),
):
    """
    Verify and update a data field in an application.

    :param payload: The data field update payload.
    :type payload: parsers.UpdateDataField

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        # Update a specific field in the application's `secop_data_verification` attribute.
        payload_dict = {key: value for key, value in payload.dict().items() if value is not None}
        key, value = next(iter(payload_dict.items()), (None, None))
        verified_data = application.secop_data_verification.copy()
        verified_data[key] = value
        application.secop_data_verification = verified_data.copy()

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.DATA_VALIDATION_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )

        return application


@router.put(
    "/applications/documents/{document_id}/verify-document",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def verify_document(
    document_id: int,
    payload: parsers.VerifyBorrowerDocument,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
):
    """
    Verify a borrower document in an application.

    :param document_id: The ID of the borrower document.
    :type document_id: int

    :param payload: The document verification payload.
    :type payload: parsers.VerifyBorrowerDocument

    :param session: The database session.
    :type session: Session

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        document = util.get_object_or_404(session, models.BorrowerDocument, "id", document_id)
        dependencies.raise_if_unauthorized(
            document.application,
            user,
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.STARTED, models.ApplicationStatus.INFORMATION_REQUESTED),
        )

        document.verified = payload.verified

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=document.application.id,
            user_id=user.id,
        )

        return document.application


@router.put(
    "/applications/{id}/award",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def update_application_award(
    id: int,
    payload: parsers.AwardUpdate,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.OCP, models.UserType.FI),
            statuses=dependencies.OCP_CAN_MODIFY,
        )
    ),
):
    """
    Update the award details of an application.

    :param payload: The award update payload.
    :type payload: parsers.AwardUpdate

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        if not application.award:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Award not found")

        # Update the award.
        update_dict = jsonable_encoder(payload, exclude_unset=True)
        application.award.update(session, **update_dict)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.AWARD_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=id,
            user_id=user.id,
        )

        application = util.get_modified_data_fields(application, session)
        return application


@router.put(
    "/applications/{id}/borrower",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def update_application_borrower(
    id: int,
    payload: parsers.BorrowerUpdate,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.OCP, models.UserType.FI),
            statuses=dependencies.OCP_CAN_MODIFY,
        )
    ),
):
    """
    Update the borrower details of an application.

    :param payload: The borrower update payload.
    :type payload: parsers.BorrowerUpdate

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    """
    with transaction_session(session):
        if not application.borrower:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrower not found")

        # Update the borrower.
        update_dict = jsonable_encoder(payload, exclude_unset=True)
        for field, value in update_dict.items():
            if not application.borrower.missing_data[field]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="This column cannot be updated",
                )
        application.borrower.update(session, **update_dict)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.BORROWER_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=id,
            user_id=user.id,
        )

        application = util.get_modified_data_fields(application, session)
        return application


@router.get(
    "/applications/admin-list",
    tags=["applications"],
    response_model=serializers.ApplicationListResponse,
)
@dependencies.OCP_only()
async def get_applications_list(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    current_user: models.User = Depends(dependencies.get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get a paginated list of submitted applications for administrative purposes.

    :param page: The page number of the application list (default: 0).
    :type page: int

    :param page_size: The number of applications per page (default: 10).
    :type page_size: int

    :param sort_field: The field to sort the applications by (default: "application.created_at").
    :type sort_field: str

    :param sort_order: The sort order of the applications ("asc" or "desc", default: "asc").
    :type sort_order: str

    :param current_user: The current user authenticated.
    :type current_user: models.User

    :param session: The database session.
    :type session: Session

    :return: The paginated list of applications.
    :rtype: serializers.ApplicationListResponse

    :raise: lumache.OCPOnlyError if the current user is not authorized.
    """
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        models.Application.submitted(session)
        .join(models.Award)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.award),
            joinedload(models.Application.borrower),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )

    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return serializers.ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/applications/id/{id}",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def get_application(
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(roles=(models.UserType.OCP, models.UserType.FI))
    ),
):
    """
    Retrieve an application by its ID.

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The application with the specified ID and its associated relations.
    :rtype: models.ApplicationWithRelations

    :raise: HTTPException with status code 401 if the user is not authorized to view the application.

    """
    return util.get_modified_data_fields(application, session)


@router.post(
    "/applications/{id}/start",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def start_application(
    id: int,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.SUBMITTED,),
        )
    ),
):
    """
    Start an application:
    Changes application status from "SUBMITTED" to "STARTED".

    :param id: The ID of the application to start.
    :type id: int

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The started application with its associated relations.
    :rtype: models.ApplicationWithRelations

    :raise: HTTPException with status code 401 if the user is not authorized to start the application.

    """
    with transaction_session(session):
        application.status = models.ApplicationStatus.STARTED
        application.lender_started_at = datetime.now(application.created_at.tzinfo)
        background_tasks.add_task(update_statistics)
        return application


@router.get(
    "/applications",
    tags=["applications"],
    response_model=serializers.ApplicationListResponse,
)
async def get_applications(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.created_at"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
):
    """
    Get a paginated list of submitted applications for a specific FI user.

    :param page: The page number of the application list (default: 0).
    :type page: int

    :param page_size: The number of applications per page (default: 10).
    :type page_size: int

    :param sort_field: The field to sort the applications by (default: "application.created_at").
    :type sort_field: str

    :param sort_order: The sort order of the applications ("asc" or "desc", default: "asc").
    :type sort_order: str

    :param user: The current user.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: The paginated list of applications for the specific user.
    :rtype: serializers.ApplicationListResponse

    """
    sort_direction = desc if sort_order.lower() == "desc" else asc

    applications_query = (
        models.Application.submitted_to_lender(session, user.lender_id)
        .join(models.Award)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.award),
            joinedload(models.Application.borrower),
        )
        .order_by(text(f"{sort_field} {sort_direction.__name__}"))
    )
    total_count = applications_query.count()

    applications = applications_query.offset(page * page_size).limit(page_size).all()

    return serializers.ApplicationListResponse(
        items=applications,
        count=total_count,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/applications/email-sme/{id}",
    tags=["applications"],
    response_model=models.ApplicationWithRelations,
)
async def email_sme(
    payload: parsers.ApplicationEmailSme,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(
            roles=(models.UserType.FI,), statuses=(models.ApplicationStatus.STARTED,)
        )
    ),
):
    """
    Send an email to SME and update the application status:
    Changes the application status from "STARTED" to "INFORMATION_REQUESTED".
    sends an email to SME notifying the request.

    :param payload: The payload containing the message to send to SME.
    :type payload: parsers.ApplicationEmailSme

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :param user: The current user.
    :type user: models.User

    :return: The updated application with its associated relations.
    :rtype: models.ApplicationWithRelations

    :raises HTTPException: If there's an error in sending the email to SME.
    """

    with transaction_session(session):
        try:
            application.status = models.ApplicationStatus.INFORMATION_REQUESTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.information_requested_at = current_time
            application.pending_documents = True

            message_id = client.send_request_to_sme(
                application.uuid,
                application.lender.name,
                payload.message,
                application.primary_email,
            )

            models.ApplicationAction.create(
                session,
                type=models.ApplicationActionType.FI_REQUEST_INFORMATION,
                data=jsonable_encoder(payload, exclude_unset=True),
                application_id=application.id,
                user_id=user.id,
            )

            models.Message.create(
                session,
                application_id=application.id,
                body=payload.message,
                lender_id=application.lender.id,
                type=models.MessageType.FI_MESSAGE,
                external_message_id=message_id,
            )

            session.commit()
            background_tasks.add_task(update_statistics)
            return application
        except ClientError as e:
            logger.exception(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error",
            )


@router.post(
    "/applications/{id}/upload-compliance",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_compliance(
    file: UploadFile,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(roles=(models.UserType.FI,))
    ),
):
    """
    Upload a compliance document for an application.

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
        new_file, filename = util.validate_file(file)

        document = util.create_or_update_borrower_document(
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


@router.get(
    "/applications/{id}/previous-awards",
    tags=["applications"],
    response_model=List[models.Award],
)
async def previous_contracts(
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_user(roles=(models.UserType.OCP, models.UserType.FI))
    ),
):
    """
    Get the previous awards associated with an application.

    :param user: The current user authenticated.
    :type user: models.User

    :param session: The database session.
    :type session: Session

    :return: A list of previous awards associated with the application.
    :rtype: List[models.Award]

    :raise: HTTPException with status code 401 if the user is not authorized to access the application.

    """
    with transaction_session(session):
        return application.previous_awards(session)
