import logging
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app import dependencies, models, parsers, serializers, util
from app.aws import CognitoClient
from app.db import get_db, transaction_session
from app.dependencies import ApplicationScope
from app.settings import app_settings
from app.utils import background
from app.utils.statistics import update_statistics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/applications/uuid/{uuid}",
    tags=["applications"],
)
async def application_by_uuid(
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_uuid(scopes=(dependencies.ApplicationScope.UNEXPIRED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Retrieve an application by its UUID.

    :return: The application with the specified UUID and its associated entities.
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
    "/applications/decline",
    tags=["applications"],
)
async def decline(
    payload: parsers.ApplicationDeclinePayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Decline an application.
    Changes application status from "PENDING" to "DECLINED".

    :param payload: The application decline payload.
    :return: The application response containing the updated application, borrower, and award.
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
)
async def rollback_decline(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Rollback the decline of an application.

    :param payload: The application base payload.
    :return: The application response containing the updated application, borrower, and award.
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
)
async def decline_feedback(
    payload: parsers.ApplicationDeclineFeedbackPayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Provide feedback for a declined application.

    :param payload: The application decline feedback payload.
    :return: The application response containing the updated application, borrower, and award.
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


@router.post(
    "/applications/access-scheme",
    tags=["applications"],
)
async def access_scheme(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Access the scheme for an application.

    Changes the status from PENDING to ACCEPTED.

    Search for previous awards for the borrower and add them to the application.

    :param payload: The application data.
    :param background_tasks: The background tasks to be executed.
    :return: The application response containing the updated application, borrower, and award.
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
)
async def credit_product_options(
    payload: parsers.ApplicationCreditOptions,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
) -> serializers.CreditProductListResponse:
    """
    Get the available credit product options for an application.

    :param payload: The application credit options.
    :return: The credit product list response containing the available loans and credit lines.
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
                col(models.Lender.id).notin_(rejecter_lenders),
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
                col(models.Lender.id).notin_(rejecter_lenders),
                filter,
            )
        )

        loans = loans_query.all()
        credit_lines = credit_lines_query.all()

        return serializers.CreditProductListResponse(loans=loans, credit_lines=credit_lines)


@router.post(
    "/applications/select-credit-product",
    tags=["applications"],
)
async def select_credit_product(
    payload: parsers.ApplicationSelectCreditProduct,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Select a credit product for an application.

    :param payload: The application credit product selection payload.
    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501
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
)
async def rollback_select_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Rollback the selection of a credit product for an application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, and award.
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
)
async def confirm_credit_product(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.ACCEPTED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Confirm the selected credit product for an application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, award, lender, documents, and credit product. # noqa: E501
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
            .order_by(col(models.Application.created_at).desc())
            .first()
        )
        if lastest_application_id:
            documents = (
                session.query(models.BorrowerDocument)
                .filter(
                    models.BorrowerDocument.application_id == lastest_application_id[0],
                    col(models.BorrowerDocument.type).in_(document_types_list),
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
)
async def update_apps_send_notifications(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            statuses=(models.ApplicationStatus.ACCEPTED,), scopes=(ApplicationScope.UNEXPIRED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Changes application status from "'ACCEPTED" to "SUBMITTED".
    Sends a notification to OCP and FI user.

    This operation also ensures that the credit product and lender are selected before updating the status.

    :param payload: The application data to update.
    :return: The updated application with borrower, award and lender details.
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error submitting the application",
            )


@router.post(
    "/applications/upload-document",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_document(
    file: UploadFile,
    type: str = Form(...),
    session: Session = Depends(get_db),
    application: models.Application = Depends(dependencies.get_publication_as_guest_via_form),
) -> Any:
    """
    Upload a document for an application.

    :param file: The uploaded file.
    :param type: The type of the document.
    :return: The created or updated borrower document.
    """
    with transaction_session(session):
        new_file, filename = util.validate_file(file)
        if not application.pending_documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload document at this stage",
            )

        document = util.create_or_update_borrower_document(
            filename, application, models.BorrowerDocumentType(type), session, new_file
        )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            data={"file_name": filename},
            application_id=application.id,
        )

        return document


@router.post(
    "/applications/complete-information-request",
    tags=["applications"],
)
async def complete_information_request(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(
            statuses=(models.ApplicationStatus.INFORMATION_REQUESTED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Complete the information request for an application:
    Changes the application from "INFORMATION REQUESTED" status back to "STARTED" and updates the pending documents status. # noqa: E501

    This operation also sends a notification about the uploaded documents to the FI.

    :param payload: The application data to update.
    :return: The updated application with borrower, award, lender, and documents details.
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
    "/applications/upload-contract",
    tags=["applications"],
    response_model=models.BorrowerDocumentBase,
)
async def upload_contract(
    file: UploadFile,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_form(statuses=(models.ApplicationStatus.APPROVED,))
    ),
) -> Any:
    """
    Upload a contract document for an application.

    :param file: The uploaded file.
    :return: The created or updated borrower document representing the contract.
    """
    with transaction_session(session):
        new_file, filename = util.validate_file(file)

        document = util.create_or_update_borrower_document(
            filename,
            application,
            models.BorrowerDocumentType.SIGNED_CONTRACT,
            session,
            new_file,
        )

        return document


@router.post(
    "/applications/confirm-upload-contract",
    tags=["applications"],
)
async def confirm_upload_contract(
    payload: parsers.UploadContractConfirmation,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(statuses=(models.ApplicationStatus.APPROVED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Confirm the upload of a contract document for an application.

    Changes application status from "CONTRACT_UPLOADED" to "CONTRACT_ACCEPTED".

    Sends an email to SME notifying the current stage of their application.

    :param payload: The confirmation data for the uploaded contract.
    :return: The application response containing the updated application and related entities.
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


@router.post(
    "/applications/find-alternative-credit-option",
    tags=["applications"],
)
async def find_alternative_credit_option(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    client: CognitoClient = Depends(dependencies.get_cognito_client),
    application: models.Application = Depends(
        dependencies.get_scoped_publication_as_guest_via_payload(statuses=(models.ApplicationStatus.REJECTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Find an alternative credit option for a rejected application by copying it.

    :param payload: The payload containing the UUID of the rejected application.
    :param client: The Cognito client for sending notifications.
    :return: The newly created application as an alternative credit option.
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
