from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col
from starlette.responses import RedirectResponse

from app import aws, dependencies, mail, models, parsers, serializers, util
from app.db import get_db, rollback_on_error
from app.i18n import _

router = APIRouter()


@router.get(
    "/applications/uuid/{uuid}",
    tags=[util.Tags.applications],
)
async def application_by_uuid(
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_uuid(scopes=(dependencies.ApplicationScope.UNEXPIRED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Retrieve an application by its UUID.

    :return: The application with the specified UUID and its associated entities.
    :raise: HTTPException if the application is expired.
    """
    return serializers.ApplicationResponse(
        application=cast(models.ApplicationRead, application),
        borrower=application.borrower,
        award=application.award,
        lender=application.lender,
        documents=cast(list[models.BorrowerDocumentBase], application.borrower_documents),
        creditProduct=application.credit_product,
    )


@router.post(
    "/applications/decline",
    tags=[util.Tags.applications],
)
async def decline(
    payload: parsers.ApplicationDeclinePayload,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Decline an application.

    Changes application status from "PENDING" to "DECLINED".

    :param payload: The application decline payload.
    :return: The application response containing the updated application, borrower, and award.
    :raise: HTTPException if the application is not in the PENDING status.
    """
    with rollback_on_error(session):
        borrower_declined_data = vars(payload)
        borrower_declined_data.pop("uuid")

        # Update application.
        application.borrower_declined_data = borrower_declined_data
        application.status = models.ApplicationStatus.DECLINED
        current_time = datetime.now(application.created_at.tzinfo)
        application.borrower_declined_at = current_time

        # Update application's borrower.
        if payload.decline_all:
            application.borrower.status = models.BorrowerStatus.DECLINE_OPPORTUNITIES
            application.borrower.declined_at = current_time

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/rollback-decline",
    tags=[util.Tags.applications],
)
async def rollback_decline(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Rollback the decline of an application.

    :param payload: The application base payload.
    :return: The application response containing the updated application, borrower, and award.
    :raise: HTTPException if the application is not in the DECLINED status.
    """
    with rollback_on_error(session):
        # Update application.
        application.borrower_declined_data = {}
        application.status = models.ApplicationStatus.PENDING
        application.borrower_declined_at = None

        # Update application's borrower.
        if application.borrower.status == models.BorrowerStatus.DECLINE_OPPORTUNITIES:
            application.borrower.status = models.BorrowerStatus.ACTIVE
            application.borrower.declined_at = None

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/decline-feedback",
    tags=[util.Tags.applications],
)
async def decline_feedback(
    payload: parsers.ApplicationDeclineFeedbackPayload,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.DECLINED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Provide feedback for a declined application.

    :param payload: The application decline feedback payload.
    :return: The application response containing the updated application, borrower, and award.
    :raise: HTTPException if the application is not in the DECLINED status.
    """
    with rollback_on_error(session):
        borrower_declined_preferences_data = vars(payload)
        borrower_declined_preferences_data.pop("uuid")

        application.borrower_declined_preferences_data = borrower_declined_preferences_data

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/access-scheme",
    tags=[util.Tags.applications],
)
async def access_scheme(
    payload: parsers.ApplicationBase,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(
            scopes=(dependencies.ApplicationScope.UNEXPIRED,), statuses=(models.ApplicationStatus.PENDING,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Access the scheme for an application.

    Changes the status from PENDING to ACCEPTED.

    Search for previous awards for the borrower and add them to the application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, and award.
    :raise: HTTPException if the application is expired or not in the PENDING status.
    """
    with rollback_on_error(session):
        application.borrower_accepted_at = datetime.now(application.created_at.tzinfo)
        application.status = models.ApplicationStatus.ACCEPTED
        application.expired_at = None

        session.commit()

        background_tasks.add_task(util.get_previous_awards_from_data_source, application.borrower_id)

        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/credit-product-options",
    tags=[util.Tags.applications],
)
async def credit_product_options(
    payload: parsers.ApplicationCreditOptions,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.CreditProductListResponse:
    """
    Get the available credit product options for an application.

    :param payload: The application credit options.
    :return: The credit product list response containing the available loans and credit lines.
    :raise: HTTPException if the application is expired, not in the ACCEPTED status, or if the
            previous lenders are not found.
    """
    base_query = (
        session.query(models.CreditProduct)
        .join(models.Lender)
        .options(joinedload(models.CreditProduct.lender))
        .filter(
            models.CreditProduct.borrower_size == payload.borrower_size,
            models.CreditProduct.lower_limit <= payload.amount_requested,
            models.CreditProduct.upper_limit >= payload.amount_requested,
            models.CreditProduct.procurement_category_to_exclude != application.award.procurement_category,
            col(models.Lender.id).notin_(application.rejected_lenders(session)),
        )
    )

    return serializers.CreditProductListResponse(
        loans=base_query.filter(models.CreditProduct.type == models.CreditType.LOAN).all(),
        credit_lines=base_query.filter(models.CreditProduct.type == models.CreditType.CREDIT_LINE).all(),
    )


@router.post(
    "/applications/select-credit-product",
    tags=[util.Tags.applications],
)
async def select_credit_product(
    payload: parsers.ApplicationSelectCreditProduct,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Select a credit product for an application.

    :param payload: The application credit product selection payload.
    :return: The application response containing the updated application, borrower, award, lender, documents, and
             credit product.
    :raise: HTTPException if the application is expired, not in the ACCEPTED status, or if the
            calculator data is invalid.
    """
    with rollback_on_error(session):
        # Extract the necessary fields for a calculator from a payload.
        calculator_data = jsonable_encoder(payload, exclude_unset=True)
        calculator_data.pop("uuid")
        calculator_data.pop("credit_product_id")
        calculator_data.pop("sector")
        calculator_data.pop("annual_revenue", "")

        # Update application.
        application.calculator_data = calculator_data
        application.credit_product_id = payload.credit_product_id
        application.borrower_credit_product_selected_at = datetime.now(application.created_at.tzinfo)

        # Update application's borrower.
        application.borrower.size = payload.borrower_size
        application.borrower.sector = payload.sector
        application.borrower.annual_revenue = payload.annual_revenue

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_CALCULATOR_DATA_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=cast(list[models.BorrowerDocumentBase], application.borrower_documents),
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/rollback-select-credit-product",
    tags=[util.Tags.applications],
)
async def rollback_select_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Rollback the selection of a credit product for an application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, and award.
    :raise: HTTPException if the credit product is not selected or if the lender is already
            assigned.
    """
    with rollback_on_error(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not selected"),
            )

        if application.lender_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Cannot rollback at this stage"),
            )

        application.credit_product_id = None
        application.borrower_credit_product_selected_at = None

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_ROLLBACK_SELECT_PRODUCT,
            application_id=application.id,
        )

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
        )


@router.post(
    "/applications/confirm-credit-product",
    tags=[util.Tags.applications],
)
async def confirm_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Confirm the selected credit product for an application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, award, lender, documents, and
             credit product.
    :raise: HTTPException if the credit product is not selected or not found.
    """
    with rollback_on_error(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not selected"),
            )

        credit_product = models.CreditProduct.first_by(session, "id", application.credit_product_id)
        if not credit_product:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not found"),
            )

        application.lender_id = credit_product.lender_id
        application.amount_requested = application.calculator_data.get("amount_requested", None)
        application.repayment_years = application.calculator_data.get("repayment_years", None)
        application.repayment_months = application.calculator_data.get("repayment_months", None)
        application.payment_start_date = application.calculator_data.get("payment_start_date", None)
        application.pending_documents = True

        # Retrieve and copy the borrower documents from the most recent rejected application
        # that shares the same award borrower identifier as the application. The documents
        # to be copied are only those whose types are required by the credit product of the
        # application.
        if latest_application_id := (
            session.query(models.Application.id)
            .filter(
                models.Application.status == models.ApplicationStatus.REJECTED,
                models.Application.award_borrower_identifier == application.award_borrower_identifier,
            )
            .order_by(col(models.Application.created_at).desc())
            .limit(1)
            .scalar()
        ):
            # Copy the documents into the database for the provided application.
            for document in session.query(models.BorrowerDocument).filter(
                models.BorrowerDocument.application_id == latest_application_id,
                col(models.BorrowerDocument.type).in_(
                    [key for key, value in application.credit_product.required_document_types.items() if value]
                ),
            ):
                application.borrower_documents.append(
                    models.BorrowerDocument.create(
                        session,
                        application_id=application.id,
                        type=document.type,
                        name=document.name,
                        file=document.file,
                        verified=False,
                    )
                )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_CONFIRM_CREDIT_PRODUCT,
            application_id=application.id,
        )

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=cast(list[models.BorrowerDocumentBase], application.borrower_documents),
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/rollback-confirm-credit-product",
    tags=[util.Tags.applications],
)
async def rollback_confirm_credit_product(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Rollback the confirmation of the selected credit product for an application.

    :param payload: The application data.
    :return: The application response containing the updated application, borrower, award, lender, documents, and
             credit product.
    :raise: HTTPException if the credit product is not selected or not found.
    """
    with rollback_on_error(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not selected"),
            )

        credit_product = models.CreditProduct.first_by(session, "id", application.credit_product_id)
        if not credit_product:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not found"),
            )

        application.lender_id = None
        application.amount_requested = None
        application.repayment_years = None
        application.repayment_months = None
        application.payment_start_date = None
        application.pending_documents = False

        # Delete the documents
        for document in application.borrower_documents:
            session.delete(document)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT,
            application_id=application.id,
        )

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=cast(list[models.BorrowerDocumentBase], application.borrower_documents),
            creditProduct=application.credit_product,
        )


@router.post(
    "/applications/submit",
    tags=[util.Tags.applications],
)
async def update_apps_send_notifications(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.ACCEPTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Change application status from "'ACCEPTED" to "SUBMITTED". Send a notification to OCP and lender user.

    This operation also ensures that the credit product and lender are selected before updating the status.

    :param payload: The application data to update.
    :return: The updated application with borrower, award and lender details.
    :raises HTTPException: If credit product or lender is not selected, or if there's an error in submitting the
            application.
    """
    with rollback_on_error(session):
        if not application.credit_product_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Credit product not selected"),
            )

        if not application.lender:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Lender not selected"),
            )

        application.status = models.ApplicationStatus.SUBMITTED
        application.borrower_submitted_at = datetime.now(application.created_at.tzinfo)
        application.pending_documents = False

        mail.send(session, client.ses, models.MessageType.NEW_APPLICATION_OCP, application, save=False)
        mail.send(session, client.ses, models.MessageType.NEW_APPLICATION_FI, application, save=False)
        mail.send(session, client.ses, models.MessageType.SUBMISSION_COMPLETED, application)

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
        )


@router.post(
    "/applications/upload-document",
    tags=[util.Tags.applications],
    response_model=models.BorrowerDocumentBase,
)
async def upload_document(
    file: UploadFile,
    type: str = Form(...),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_form(
            statuses=(
                models.ApplicationStatus.ACCEPTED,
                models.ApplicationStatus.INFORMATION_REQUESTED,
                models.ApplicationStatus.APPROVED,
            )
        )
    ),
) -> Any:
    """
    Upload a document for an application.

    :param file: The uploaded file.
    :param type: The type of the document.
    :return: The created or updated borrower document.
    """
    with rollback_on_error(session):
        new_file, filename = util.validate_file(file)
        if not application.pending_documents:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=_("Cannot upload document at this stage"),
            )

        document = util.create_or_update_borrower_document(
            session, filename, application, models.BorrowerDocumentType(type), new_file
        )

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_DOCUMENT,
            data={"file_name": filename},
            application_id=application.id,
        )

        session.commit()
        return document


@router.post(
    "/applications/complete-information-request",
    tags=[util.Tags.applications],
)
async def complete_information_request(
    payload: parsers.ApplicationBase,
    client: aws.Client = Depends(dependencies.get_aws_client),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(
            statuses=(models.ApplicationStatus.INFORMATION_REQUESTED,)
        )
    ),
) -> serializers.ApplicationResponse:
    """
    Complete the information request for an application.

    Changes application status from "INFORMATION REQUESTED" to "STARTED" and update the pending documents status.

    This operation also sends a notification about the uploaded documents to the lender.

    :param payload: The application data to update.
    :return: The updated application with borrower, award, lender, and documents details.
    """
    with rollback_on_error(session):
        application.status = models.ApplicationStatus.STARTED
        application.pending_documents = False

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
        )

        mail.send(session, client.ses, models.MessageType.BORROWER_DOCUMENT_UPDATED, application)

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, application),
            borrower=application.borrower,
            award=application.award,
            lender=application.lender,
            documents=cast(list[models.BorrowerDocumentBase], application.borrower_documents),
        )


@router.post(
    "/applications/find-alternative-credit-option",
    tags=[util.Tags.applications],
)
async def find_alternative_credit_option(
    payload: parsers.ApplicationBase,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_payload(statuses=(models.ApplicationStatus.REJECTED,))
    ),
) -> serializers.ApplicationResponse:
    """
    Find an alternative credit option for a rejected application by copying it.

    :param payload: The payload containing the UUID of the rejected application.
    :param client: The Cognito client for sending notifications.
    :return: The newly created application as an alternative credit option.
    :raise: HTTPException if the application has already been copied.
    :raise: HTTPException if the application is not in the rejected status.
    """
    with rollback_on_error(session):
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
                detail=_("A new application has already been created from this one"),
            )

        # Copy the application, changing the uuid, status, and borrower_accepted_at.
        new_application = models.Application.create(
            session,
            award_id=application.award_id,
            uuid=util.generate_uuid(application.uuid),
            primary_email=application.primary_email,
            status=models.ApplicationStatus.ACCEPTED,
            award_borrower_identifier=application.award_borrower_identifier,
            borrower_id=application.borrower.id,
            calculator_data=application.calculator_data,
            borrower_accepted_at=datetime.now(application.created_at.tzinfo),
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

        mail.send(session, client.ses, models.MessageType.APPLICATION_COPIED, new_application)

        session.commit()
        return serializers.ApplicationResponse(
            application=cast(models.ApplicationRead, new_application),
            borrower=new_application.borrower,
            award=new_application.award,
        )


@router.get(
    "/applications/uuid/{uuid}/access-external-onboarding",
    tags=[util.Tags.applications],
)
async def access_external_onboarding(
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_uuid(
            statuses=(models.ApplicationStatus.SUBMITTED, models.ApplicationStatus.STARTED)
        ),
    ),
) -> RedirectResponse:
    """
    :return: A redirect to the lender.external_onboarding_url.
    :raise: HTTPException if the application has a lender without an external_onboarding_url.
    """
    return util.handle_external_onboarding(session, application, forward=True)


@router.get(
    "/applications/uuid/{uuid}/accessed-external-onboarding",
    tags=[util.Tags.applications],
)
async def accessed_external_onboarding(
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_guest_via_uuid(
            statuses=(models.ApplicationStatus.SUBMITTED, models.ApplicationStatus.STARTED)
        ),
    ),
) -> RedirectResponse:
    """
    Report having started external onboarding.

    :return: A redirect to the frontend's external-onboarding-completed page.
    :raise: HTTPException if the application has a lender without an external_onboarding_url.
    """
    return util.handle_external_onboarding(session, application)
