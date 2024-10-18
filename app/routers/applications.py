from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app import aws, dependencies, mail, models, parsers, serializers, util
from app.db import get_db, rollback_on_error
from app.i18n import _
from app.util import SortOrder

router = APIRouter()


@router.post(
    "/applications/{id}/reject-application",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def reject_application(
    payload: parsers.LenderRejectedApplication,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.STARTED,),
        )
    ),
) -> Any:
    """
    Reject an application.

    Changes application status from "STARTED" to "REJECTED".

    :param payload: The rejected application data.
    :return: The rejected application with its associated relations.
    """
    with rollback_on_error(session):
        payload_dict = jsonable_encoder(payload, exclude_unset=True)
        application.stage_as_rejected(payload_dict)

        options = session.query(
            session.query(models.CreditProduct)
            .join(models.Lender)
            .options(joinedload(models.CreditProduct.lender))
            .filter(
                models.CreditProduct.borrower_size == application.borrower.size,
                models.CreditProduct.lender_id != application.lender_id,
                col(models.CreditProduct.lower_limit) <= application.amount_requested,
                col(models.CreditProduct.upper_limit) >= application.amount_requested,
            )
            .exists()
        ).scalar()

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.REJECTED_APPLICATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )

        mail.send(session, client.ses, models.MessageType.REJECTED_APPLICATION, application, options=options)

        session.commit()
        return application


@router.post(
    "/applications/{id}/approve-application",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def approve_application(
    payload: parsers.LenderApprovedData,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.STARTED,),
        )
    ),
) -> Any:
    """
    Approve an application.

    Change application status from "STARTED" to "APPROVED". Notify the borrower of the approval.

    :param payload: The approved application data.
    :return: The approved application with its associated relations.
    """
    with rollback_on_error(session):
        # If the lender has an external onboarding system, the fields and documents verification is not required.
        if not application.lender.external_onboarding_url:
            # Check if all keys present in an instance of UpdateDataField exist and have truthy values in
            # the application's `secop_data_verification`.
            app_secop_dict = application.secop_data_verification.copy()
            fields = list(parsers.UpdateDataField().model_dump().keys())
            if any(not app_secop_dict.get(key) for key in fields):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=_("Some borrower data field are not verified"),
                )

            # Check all documents are verified.
            if any(not doc.verified for doc in application.borrower_documents):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=_("Some documents are not verified"),
                )

        # Approve the application.
        application.stage_as_approved(payload.disbursed_final_amount, jsonable_encoder(payload, exclude_unset=True))
        application.completed_in_days = application.days_waiting_for_lender(session)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.APPROVED_APPLICATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )

        mail.send(session, client.ses, models.MessageType.APPROVED_APPLICATION, application)

        session.commit()
        return application


@router.put(
    "/applications/{id}/verify-data-field",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def verify_data_field(
    payload: parsers.UpdateDataField,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.FI,),
            statuses=(
                models.ApplicationStatus.STARTED,
                models.ApplicationStatus.INFORMATION_REQUESTED,
            ),
        )
    ),
) -> Any:
    """
    Verify and update a data field in an application.

    :param payload: The data field update payload.
    :return: The updated application with its associated relations.
    """
    with rollback_on_error(session):
        # Update a specific field in the application's `secop_data_verification` attribute.
        payload_dict = {key: value for key, value in payload.model_dump().items() if value is not None}
        try:
            key, value = next(iter(payload_dict.items()))
        except StopIteration:
            return application

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

        session.commit()
        return application


@router.put(
    "/applications/documents/{document_id}/verify-document",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def verify_document(
    document_id: int,
    payload: parsers.VerifyBorrowerDocument,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
) -> Any:
    """
    Verify a borrower document in an application.

    :param document_id: The ID of the borrower document.
    :param payload: The document verification payload.
    :return: The updated application with its associated relations.
    """
    with rollback_on_error(session):
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
            type=models.ApplicationActionType.BORROWER_DOCUMENT_VERIFIED,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=document.application.id,
            user_id=user.id,
        )

        session.commit()
        return document.application


@router.put(
    "/applications/{id}/award",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def update_application_award(
    id: int,
    payload: parsers.AwardUpdate,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.OCP, models.UserType.FI),
            statuses=dependencies.USER_CAN_EDIT_AWARD_BORROWER_DATA,
        )
    ),
) -> Any:
    """
    Update the award details of an application.

    :param payload: The award update payload.
    :return: The updated application with its associated relations.
    """
    with rollback_on_error(session):
        if not application.award:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_("Award not found"),
            )

        # Update the award.
        application.award.update(session, **jsonable_encoder(payload, exclude_unset=True))

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.AWARD_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=id,
            user_id=user.id,
        )

        session.commit()
        return util.get_modified_data_fields(session, application)


@router.put(
    "/applications/{id}/borrower",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def update_application_borrower(
    id: int,
    payload: parsers.BorrowerUpdate,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.OCP, models.UserType.FI),
            statuses=dependencies.USER_CAN_EDIT_AWARD_BORROWER_DATA,
        )
    ),
) -> Any:
    """
    Update the borrower details of an application.

    :param payload: The borrower update payload.
    :return: The updated application with its associated relations.
    """
    with rollback_on_error(session):
        if not application.borrower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_("Borrower not found"),
            )

        # Update the borrower.
        update_dict = jsonable_encoder(payload, exclude_unset=True)
        for field in update_dict:
            if not application.borrower.missing_data[field]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=_("This column cannot be updated"),
                )
        application.borrower.update(session, **update_dict)

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.BORROWER_UPDATE,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=id,
            user_id=user.id,
        )

        session.commit()
        return util.get_modified_data_fields(session, application)


@router.get(
    "/applications/admin-list",
    tags=[util.Tags.applications],
)
async def get_applications_list(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.borrower_submitted_at"),
    sort_order: SortOrder = Query("asc"),
    search_value: str = "",
    admin: models.User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> serializers.ApplicationListResponse:
    """Get a paginated list of submitted applications for administrative purposes."""
    applications_query = models.Application.submitted_search(
        session, search_value=search_value, sort_field=sort_field, sort_order=sort_order
    )

    total_count = applications_query.count()

    applications = applications_query.limit(page_size).offset(page * page_size).all()

    return serializers.ApplicationListResponse(
        items=cast(list[models.ApplicationWithRelations], applications),
        count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/applications",
    tags=[util.Tags.applications],
)
async def get_applications(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, gt=0),
    sort_field: str = Query("application.borrower_submitted_at"),
    sort_order: SortOrder = Query("asc"),
    search_value: str = "",
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
) -> serializers.ApplicationListResponse:
    """Get a paginated list of submitted applications for a specific lender user."""
    applications_query = models.Application.submitted_search(
        session, search_value=search_value, sort_field=sort_field, sort_order=sort_order, lender_id=user.lender_id
    )

    total_count = applications_query.count()

    applications = applications_query.limit(page_size).offset(page * page_size).all()

    return serializers.ApplicationListResponse(
        items=cast(list[models.ApplicationWithRelations], applications),
        count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/applications/id/{id}",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def get_application(
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(roles=(models.UserType.OCP, models.UserType.FI))
    ),
) -> Any:
    """
    Retrieve an application by its ID.

    :return: The application with the specified ID and its associated relations.
    :raise: HTTPException if the user is not authorized to view the application.
    """
    return util.get_modified_data_fields(session, application)


@router.post(
    "/applications/{id}/start",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def start_application(
    id: int,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.FI,),
            statuses=(models.ApplicationStatus.SUBMITTED,),
        )
    ),
) -> Any:
    """
    Start an application.

    Change application status from "SUBMITTED" to "STARTED".

    :param id: The ID of the application to start.
    :return: The started application with its associated relations.
    :raise: HTTPException if the user is not authorized to start the application.
    """
    with rollback_on_error(session):
        application.status = models.ApplicationStatus.STARTED
        application.lender_started_at = datetime.now(application.created_at.tzinfo)

        session.commit()
        return application


@router.post(
    "/applications/email-sme/{id}",
    tags=[util.Tags.applications],
    response_model=models.ApplicationWithRelations,
)
async def email_borrower(
    payload: parsers.ApplicationEmailBorrower,
    session: Session = Depends(get_db),
    client: aws.Client = Depends(dependencies.get_aws_client),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.FI,),
            scopes=(dependencies.ApplicationScope.NATIVE,),
            statuses=(models.ApplicationStatus.STARTED,),
        )
    ),
) -> Any:
    """
    Send an email to the borrower and update the application status.

    Change application status from "STARTED" to "INFORMATION_REQUESTED". Notify the borrower of the request.

    :param payload: The payload containing the message to send to the borrower.
    :return: The updated application with its associated relations.
    :raises HTTPException: If there's an error in sending the email to the borrower.
    """
    with rollback_on_error(session):
        application.status = models.ApplicationStatus.INFORMATION_REQUESTED
        application.information_requested_at = datetime.now(application.created_at.tzinfo)
        application.pending_documents = True

        models.ApplicationAction.create(
            session,
            type=models.ApplicationActionType.FI_REQUEST_INFORMATION,
            data=jsonable_encoder(payload, exclude_unset=True),
            application_id=application.id,
            user_id=user.id,
        )

        mail.send(
            session,
            client.ses,
            models.MessageType.FI_MESSAGE,
            application,
            message=payload.message,
            save_kwargs={"body": payload.message, "lender_id": application.lender.id},
        )

        session.commit()
        return application


@router.get(
    "/applications/{id}/previous-awards",
    tags=[util.Tags.applications],
)
async def previous_contracts(
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(roles=(models.UserType.OCP, models.UserType.FI))
    ),
) -> list[models.Award]:
    """
    Get the previous awards associated with an application.

    :return: A list of previous awards associated with the application.
    :raise: HTTPException if the user is not authorized to access the application.
    """
    return application.previous_awards(session)
