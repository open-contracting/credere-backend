import logging
from datetime import datetime
from typing import List

from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, parsers, serializers, util
from app.aws import CognitoClient
from app.db import get_db, transaction_session
from app.settings import app_settings
from app.utils import background
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
    application: models.Application = Depends(dependencies.get_authorized_application(roles=(models.UserType.FI,))),
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
        dependencies.get_authorized_application(
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
        dependencies.get_authorized_application(
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


@router.post(
    "/applications/confirm-upload-contract",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def confirm_upload_contract(
    payload: parsers.UploadContractConfirmation,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(statuses=(models.ApplicationStatus.APPROVED,))
    ),
):
    """
    Confirm the upload of a contract document for an application.

    Changes application status from "CONTRACT_UPLOADED" to "CONTRACT_ACCEPTED".

    Sends an email to SME notifying the current stage of their application.

    :param payload: The confirmation data for the uploaded contract.
    :type payload: parsers.UploadContractConfirmation

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The application response containing the updated application and related entities.
    :rtype: serializers.ApplicationResponse

    """
    with transaction_session(session):
        FI_message_id, SME_message_id = client.send_upload_contract_notifications(application)

        application.contract_amount_submitted = payload.contract_amount_submitted
        application.status = models.ApplicationStatus.CONTRACT_UPLOADED
        application.borrower_uploaded_contract_at = datetime.now(application.created_at.tzinfo)

        models.Message.create(
            session,
            application=application,
            type=models.MessageType.CONTRACT_UPLOAD_CONFIRMATION_TO_FI,
            external_message_id=FI_message_id,
        )

        models.Message.create(
            session,
            application=application,
            type=models.MessageType.CONTRACT_UPLOAD_CONFIRMATION,
            external_message_id=SME_message_id,
        )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_CONTRACT,
            # payload.contract_amount_submitted is a Decimal.
            data=jsonable_encoder({"contract_amount_submitted": payload.contract_amount_submitted}),
            application_id=application.id,
        )

        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


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
        dependencies.get_authorized_application(
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
        dependencies.raise_if_application_not_to_lender(document.application, user)
        dependencies.raise_if_application_status_mismatch(
            document.application, (models.ApplicationStatus.STARTED, models.ApplicationStatus.INFORMATION_REQUESTED)
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
        dependencies.get_authorized_application(
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
        dependencies.get_authorized_application(
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
        dependencies.get_authorized_application(roles=(models.UserType.OCP, models.UserType.FI))
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
        dependencies.get_authorized_application(
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


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def application_by_uuid(
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_uuid(scopes=(dependencies.ApplicationScope.UNEXPIRED,))
    ),
):
    """
    Retrieve an application by its UUID.

    :param session: The database session.
    :type session: Session

    :return: The application with the specified UUID and its associated entities.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired.

    """
    return serializers.ApplicationResponse(
        application=application,
        borrower=application.borrower,
        award=application.award,
        lender=application.lender,
        documents=application.borrower_documents,
        creditProduct=application.credit_product,
    )


@router.post(
    "/applications/access-scheme",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def access_scheme(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
):
    """
    Access the scheme for an application.

    Changes the status from PENDING to ACCEPTED.

    Search for previous awards for the borrower and add them to the application.


    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param background_tasks: The background tasks to be executed.
    :type background_tasks: BackgroundTasks

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired or not in the PENDING status.

    """
    with transaction_session(session):
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_accepted_at = current_time
        application.status = models.ApplicationStatus.ACCEPTED
        application.expired_at = None

        background_tasks.add_task(background.fetch_previous_awards, application.borrower)
        background_tasks.add_task(update_statistics)

        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/credit-product-options",
    tags=["applications"],
    response_model=serializers.CreditProductListResponse,
)
async def credit_product_options(
    payload: parsers.ApplicationCreditOptions,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
):
    """
    Get the available credit product options for an application.

    :param payload: The application credit options.
    :type payload: parsers.ApplicationCreditOptions

    :param session: The database session.
    :type session: Session

    :return: The credit product list response containing the available loans and credit lines.
    :rtype: serializers.CreditProductListResponse

    :raise: HTTPException with status code 404 if the application is expired, not in the ACCEPTED status, or if the previous lenders are not found. # noqa

    """
    with transaction_session(session):
        rejecter_lenders = application.rejecter_lenders(session)

        filter = None
        if application.borrower.type.lower() == "persona natural colombiana":
            filter = text(f"(borrower_types->>'{models.BorrowerType.NATURAL_PERSON.value}')::boolean is True")
        else:
            filter = text(f"(borrower_types->>'{models.BorrowerType.LEGAL_PERSON.value}')::boolean is True")

        loans_query = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                models.CreditProduct.type == models.CreditType.LOAN,
                models.CreditProduct.borrower_size == payload.borrower_size,
                models.CreditProduct.lower_limit <= payload.amount_requested,
                models.CreditProduct.upper_limit >= payload.amount_requested,
                models.Lender.id.notin_(rejecter_lenders),
                filter,
            )
        )

        credit_lines_query = (
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                models.CreditProduct.type == models.CreditType.CREDIT_LINE,
                models.CreditProduct.borrower_size == payload.borrower_size,
                models.CreditProduct.lower_limit <= payload.amount_requested,
                models.CreditProduct.upper_limit >= payload.amount_requested,
                models.Lender.id.notin_(rejecter_lenders),
                filter,
            )
        )

        loans = loans_query.all()
        credit_lines = credit_lines_query.all()

        return serializers.CreditProductListResponse(loans=loans, credit_lines=credit_lines)


@router.post(
    "/applications/select-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def select_credit_product(
    payload: parsers.ApplicationSelectCreditProduct,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
):
    """
    Select a credit product for an application.

    :param payload: The application credit product selection payload.
    :type payload: parsers.ApplicationSelectCreditProduct

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 404 if the application is expired, not in the ACCEPTED status, or if the calculator data is invalid. # noqa: E501

    """
    with transaction_session(session):
        # Extract the necessary fields for a calculator from a payload.
        calculator_data = jsonable_encoder(payload, exclude_unset=True)
        calculator_data.pop("uuid")
        calculator_data.pop("credit_product_id")
        calculator_data.pop("sector")

        application.calculator_data = calculator_data
        application.credit_product_id = payload.credit_product_id
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_credit_product_selected_at = current_time

        application.borrower.size = payload.borrower_size
        application.borrower.sector = payload.sector

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_CALCULATOR_DATA_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/rollback-select-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def rollback_select_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
):
    """
    Rollback the selection of a credit product for an application.

    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the credit product is not selected or if the lender is already assigned. # noqa: E501

    """
    with transaction_session(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not selected",
            )

        if application.lender_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rollback at this stage",
            )

        application.credit_product_id = None
        application.borrower_credit_product_selected_at = None
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/confirm-credit-product",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def confirm_credit_product(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
):
    """
    Confirm the selected credit product for an application.

    :param payload: The application data.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501

    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the credit product is not selected or not found.

    """
    with transaction_session(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not selected",
            )

        creditProduct = models.CreditProduct.first_by(session, "id", application.credit_product_id)
        if not creditProduct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit product not found",
            )

        application.lender_id = creditProduct.lender_id
        application.amount_requested = application.calculator_data.get("amount_requested", None)
        application.repayment_years = application.calculator_data.get("repayment_years", None)
        application.repayment_months = application.calculator_data.get("repayment_months", None)
        application.payment_start_date = application.calculator_data.get("payment_start_date", None)

        application.pending_documents = True

        # Retrieve and copy the borrower documents from the most recent rejected application
        # that shares the same award borrower identifier as the application. The documents
        # to be copied are only those whose types are required by the credit product of the
        # application.
        document_types = application.credit_product.required_document_types
        document_types_list = [key for key, value in document_types.items() if value]
        lastest_application_id = (
            session.query(models.Application.id)
            .filter(
                models.Application.status == models.ApplicationStatus.REJECTED,
                models.Application.award_borrower_identifier == application.award_borrower_identifier,
            )
            .order_by(models.Application.created_at.desc())
            .first()
        )
        if lastest_application_id:
            documents = (
                session.query(models.BorrowerDocument)
                .filter(
                    models.BorrowerDocument.application_id == lastest_application_id[0],
                    models.BorrowerDocument.type.in_(document_types_list),
                )
                .all()
            )

            # Copy the documents into the database for the provided application.
            for document in documents:
                data = {
                    "application_id": application.id,
                    "type": document.type,
                    "name": document.name,
                    "file": document.file,
                    "verified": False,
                }
                new_borrower_document = models.BorrowerDocument.create(session, **data)
                application.borrower_documents.append(new_borrower_document)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_CONFIRM_CREDIT_PRODUCT,
            application_id=application.id,
        )
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/submit",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def update_apps_send_notifications(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
):
    """
    Changes application status from "'ACCEPTED" to "SUBMITTED".
    Sends a notification to OCP and FI user.

    This operation also ensures that the credit product and lender are selected before updating the status.

    :param payload: The application data to update.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client.
    :type client: CognitoClient

    :return: The updated application with borrower, award and lender details.
    :rtype: serializers.ApplicationResponse

    :raises HTTPException: If credit product or lender is not selected, or if there's an error in submitting the application. # noqa: E501
    """
    with transaction_session(session):
        try:
            if not application.credit_product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit product not selected",
                )

            if not application.lender:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Lender not selected",
                )

            application.status = models.ApplicationStatus.SUBMITTED
            current_time = datetime.now(application.created_at.tzinfo)
            application.borrower_submitted_at = current_time
            application.pending_documents = False

            client.send_notifications_of_new_applications(
                ocp_email_group=app_settings.ocp_email_group,
                lender_name=application.lender.name,
                lender_email_group=application.lender.email_group,
            )
            message_id = client.send_application_submission_completed(application)
            models.Message.create(
                session,
                application=application,
                type=models.MessageType.SUBMITION_COMPLETE,
                external_message_id=message_id,
            )
            background_tasks.add_task(update_statistics)
            return serializers.ApplicationResponse(
                application=application,
                borrower=application.borrower,
                award=application.award,
                lender=application.lender,
            )
        except ClientError as e:
            logger.exception(e)
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error submiting the application",
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
        dependencies.get_authorized_application(
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
    "/applications/complete-information-request",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def complete_information_request(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(statuses=(models.ApplicationStatus.INFORMATION_REQUESTED,))
    ),
):
    """
    Complete the information request for an application:
    Changes the application from "INFORMATION REQUESTED" status back to "STARTED" and updates the pending documents status. # noqa: E501

    This operation also sends a notification about the uploaded documents to the FI.

    :param payload: The application data to update.
    :type payload: parsers.ApplicationBase

    :param client: The Cognito client.
    :type client: CognitoClient

    :param session: The database session.
    :type session: Session

    :return: The updated application with borrower, award, lender, and documents details.
    :rtype: serializers.ApplicationResponse

    """

    with transaction_session(session):
        application.status = models.ApplicationStatus.STARTED
        application.pending_documents = False

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        message_id = client.send_upload_documents_notifications(application.lender.email_group)

        models.Message.create(
            session,
            application=application,
            type=models.ApplicationActionType.BORROWER_DOCUMENT_UPDATE,
            external_message_id=message_id,
        )
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=application.borrower_documents,
        )


@router.post(
    "/applications/decline",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def decline(
    payload: parsers.ApplicationDeclinePayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
):
    """
    Decline an application.
    Changes application status from "PENDING" to "DECLINED".

    :param payload: The application decline payload.
    :type payload: parsers.ApplicationDeclinePayload

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the PENDING status.

    """
    with transaction_session(session):
        borrower_declined_data = vars(payload)
        borrower_declined_data.pop("uuid")

        application.borrower_declined_data = borrower_declined_data
        application.status = models.ApplicationStatus.DECLINED
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_declined_at = current_time

        if payload.decline_all:
            application.borrower.status = models.BorrowerStatus.DECLINE_OPPORTUNITIES
            application.borrower.declined_at = current_time
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/rollback-decline",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def rollback_decline(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
):
    """
    Rollback the decline of an application.

    :param payload: The application base payload.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the DECLINED status.

    """
    with transaction_session(session):
        application.borrower_declined_data = {}
        application.status = models.ApplicationStatus.PENDING
        application.borrower_declined_at = None

        if application.borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
            application.borrower.status = models.BorrowerStatus.ACTIVE
            application.borrower.declined_at = None
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/decline-feedback",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def decline_feedback(
    payload: parsers.ApplicationDeclineFeedbackPayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
):
    """
    Provide feedback for a declined application.

    :param payload: The application decline feedback payload.
    :type payload: parsers.ApplicationDeclineFeedbackPayload

    :param session: The database session.
    :type session: Session

    :return: The application response containing the updated application, borrower, and award.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application is not in the DECLINED status.

    """
    with transaction_session(session):
        borrower_declined_preferences_data = vars(payload)
        borrower_declined_preferences_data.pop("uuid")

        application.borrower_declined_preferences_data = borrower_declined_preferences_data
        background_tasks.add_task(update_statistics)
        return serializers.ApplicationResponse(
            application=application,
            borrower=application.borrower,
            award=application.award,
        )


@router.get(
    "/applications/{id}/previous-awards",
    tags=["applications"],
    response_model=List[models.Award],
)
async def previous_contracts(
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_authorized_application(roles=(models.UserType.OCP, models.UserType.FI))
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


@router.post(
    "/applications/find-alternative-credit-option",
    tags=["applications"],
    response_model=serializers.ApplicationResponse,
)
async def find_alternative_credit_option(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_application_by_payload(statuses=(models.ApplicationStatus.REJECTED,))
    ),
):
    """
    Find an alternative credit option for a rejected application by copying it.

    :param payload: The payload containing the UUID of the rejected application.
    :type payload: parsers.ApplicationBase

    :param session: The database session.
    :type session: Session

    :param client: The Cognito client for sending notifications.
    :type client: CognitoClient

    :return: The newly created application as an alternative credit option.
    :rtype: serializers.ApplicationResponse

    :raise: HTTPException with status code 400 if the application has already been copied.
    :raise: HTTPException with status code 400 if the application is not in the rejected status.

    """
    with transaction_session(session):
        # Check if the application has already been copied.
        app_action = (
            session.query(models.ApplicationAction)
            .join(
                models.Application,
                models.Application.id == models.ApplicationAction.application_id,
            )
            .filter(
                models.Application.id == application.id,
                models.ApplicationAction.type == models.ApplicationActionType.COPIED_APPLICATION,
            )
            .options(joinedload(models.ApplicationAction.application))
            .first()
        )
        if app_action:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=util.ERROR_CODES.APPLICATION_ALREADY_COPIED.value,
            )

        # Copy the application, changing the uuid, status, and borrower_accepted_at.
        try:
            data = {
                "award_id": application.award_id,
                "uuid": util.generate_uuid(application.uuid),
                "primary_email": application.primary_email,
                "status": models.ApplicationStatus.ACCEPTED,
                "award_borrower_identifier": application.award_borrower_identifier,
                "borrower_id": application.borrower.id,
                "calculator_data": application.calculator_data,
                "borrower_accepted_at": datetime.now(application.created_at.tzinfo),
            }
            new_application = models.Application.create(session, **data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"There was a problem copying the application.{e}",
            )

        message_id = client.send_copied_application_notifications(new_application)

        models.Message.create(
            session,
            application=new_application,
            type=models.MessageType.APPLICATION_COPIED,
            external_message_id=message_id,
        )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.COPIED_APPLICATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )
        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_COPIED_FROM,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=new_application.id,
        )

        return serializers.ApplicationResponse(
            application=new_application,
            borrower=new_application.borrower,
            award=new_application.award,
        )
