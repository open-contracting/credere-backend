import io
import zipfile
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session, joinedload

from app import dependencies, models, util
from app.db import get_db, rollback_on_error
from app.dependencies import ApplicationScope
from app.i18n import get_translated_string
from app.utils import tables
from reportlab_mods import styleSubTitle, styleTitle

router = APIRouter()


@router.get(
    "/applications/documents/id/{id}",
    tags=["applications"],
)
async def get_borrower_document(
    id: int,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
) -> Response:
    """
    Retrieve a borrower document by its ID and stream the file content as a response.

    :param id: The ID of the borrower document to retrieve.
    :return: A streaming response with the borrower document file content.
    """
    with rollback_on_error(session):
        document = util.get_object_or_404(session, models.BorrowerDocument, "id", id)
        dependencies.raise_if_unauthorized(document.application, user, roles=(models.UserType.OCP, models.UserType.FI))

        if user.is_ocp():
            models.ApplicationAction.create(
                session,
                type=models.ApplicationActionType.OCP_DOWNLOAD_DOCUMENT,
                data={"file_name": document.name},
                application_id=document.application.id,
            )
        else:
            models.ApplicationAction.create(
                session,
                type=models.ApplicationActionType.FI_DOWNLOAD_DOCUMENT,
                data={"file_name": document.name},
                application_id=document.application.id,
            )

        session.commit()
        return Response(
            content=document.file,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{document.name}"'},
        )


@router.get(
    "/applications/{id}/download-application/{lang}",
    tags=["applications"],
)
async def download_application(
    lang: str,
    session: Session = Depends(get_db),
    user: models.User = Depends(dependencies.get_user),
    application: models.Application = Depends(
        dependencies.get_scoped_application_as_user(
            roles=(models.UserType.OCP, models.UserType.FI), scopes=(ApplicationScope.UNEXPIRED,)
        )
    ),
) -> Response:
    """
    Retrieve all documents related to an application and stream them as a zip file.

    :return: A streaming response with a zip file containing the documents.
    """
    with rollback_on_error(session):
        borrower = application.borrower
        award = application.award
        documents = list(application.borrower_documents)

        previous_awards = application.previous_awards(session)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        elements: list[Any] = []

        elements.append(Paragraph(get_translated_string("Application Details", lang), styleTitle))

        elements.append(tables.create_application_table(application, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_borrower_table(borrower, application, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_documents_table(documents, lang))
        elements.append(Spacer(1, 20))
        elements.append(tables.create_award_table(award, lang))

        if previous_awards and len(previous_awards) > 0:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(get_translated_string("Previous Public Sector Contracts", lang), styleSubTitle))
            for award in previous_awards:
                elements.append(tables.create_award_table(award, lang))
                elements.append(Spacer(1, 20))

        doc.build(elements)

        name = get_translated_string("Application Details", lang).replace(" ", "_")
        filename = f"{name}-{application.borrower.legal_identifier}-{application.award.source_contract_id}.pdf"

        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, "w") as zip_file:
            zip_file.writestr(filename, buffer.getvalue())
            for document in documents:
                zip_file.writestr(document.name, document.file)

        application_action_type = (
            models.ApplicationActionType.OCP_DOWNLOAD_APPLICATION
            if user.is_ocp()
            else models.ApplicationActionType.FI_DOWNLOAD_APPLICATION
        )
        models.ApplicationAction.create(
            session,
            type=application_action_type,
            application_id=application.id,
            user_id=user.id,
        )

        session.commit()
        return Response(
            content=in_memory_zip.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@router.get(
    "/applications/export/{lang}",
    tags=["applications"],
)
async def export_applications(
    lang: str,
    user: models.User = Depends(dependencies.get_user),
    session: Session = Depends(get_db),
) -> Response:
    applications_query = (
        models.Application.submitted_to_lender(session, user.lender_id)
        .join(models.Borrower)
        .options(
            joinedload(models.Application.borrower),
        )
    )
    applicants_list = []
    for application in applications_query.all():
        applicants_list.append(
            {
                get_translated_string("National Tax ID", lang): application.borrower.legal_identifier,
                get_translated_string("Legal Name", lang): application.borrower.legal_name,
                get_translated_string("Email Address", lang): application.primary_email,
                get_translated_string("Submission Date", lang): application.borrower_submitted_at,
                get_translated_string("Stage", lang): get_translated_string(application.status.capitalize(), lang),
            }
        )

    df = pd.DataFrame(applicants_list)
    stream = io.StringIO()
    df.to_csv(stream, index=False)

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )
