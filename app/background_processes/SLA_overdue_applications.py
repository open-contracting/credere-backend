import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

from app.core.settings import app_settings
from app.core.user_dependencies import sesClient
from app.db.session import get_db
from app.schema import core
from app.utils import email_utility

from . import application_utils

get_all_applications_with_status = application_utils.get_all_applications_with_status
create_message = application_utils.create_message


def SLA_overdue_applications():
    with contextmanager(get_db)() as session:
        applications = get_all_applications_with_status(
            [
                core.ApplicationStatus.INFORMATION_REQUESTED,
                core.ApplicationStatus.STARTED,
            ],
            session,
        )
        overdue_lenders = defaultdict(lambda: {"count": 0})
        for application in applications:
            application = (
                session.query(core.Application)
                .filter(core.Application.id == application.id)
                .first()
            )
            paired_actions = []
            fi_request_actions = (
                session.query(core.ApplicationAction)
                .filter(core.ApplicationAction.application_id == application.id)
                .filter(core.ApplicationAction.type == "FI_REQUEST_INFORMATION")
                .order_by(core.ApplicationAction.created_at)
                .all()
            )
            if fi_request_actions:
                first_information_request = fi_request_actions.pop(0)
                paired_actions.append(
                    (
                        first_information_request.created_at,
                        application.lender_started_at,
                    )
                )
            else:
                current_dt = datetime.now(application.created_at.tzinfo)
                paired_actions.append(
                    (
                        current_dt,
                        application.lender_started_at,
                    )
                )

            msme_upload_actions = (
                session.query(core.ApplicationAction)
                .filter(core.ApplicationAction.application_id == application.id)
                .filter(
                    core.ApplicationAction.type
                    == "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED"
                )
                .order_by(core.ApplicationAction.created_at)
                .all()
            )

            for msme_upload_action in msme_upload_actions:
                if not fi_request_actions:
                    current_dt = datetime.now(application.created_at.tzinfo)
                    paired_actions.append((current_dt, msme_upload_action.created_at))
                    break
                else:
                    fi_request_action = fi_request_actions.pop(0)
                    paired_actions.append(
                        (fi_request_action.created_at, msme_upload_action.created_at)
                    )

            days_passed = 0
            for fi_request_action, msme_upload_action in paired_actions:
                days_passed += (fi_request_action - msme_upload_action).days

            days_passed = round(days_passed)
            application.completed_in_days = days_passed

            if (
                days_passed
                > application.lender.sla_days
                * app_settings.progress_to_remind_started_applications
            ):
                if "email" not in overdue_lenders[application.lender.email_group]:
                    overdue_lenders[application.lender.email_group][
                        "email"
                    ] = application.lender.email_group
                    overdue_lenders[application.lender.email_group][
                        "name"
                    ] = application.lender.name
                overdue_lenders[application.lender.email_group]["count"] += 1
                if (
                    days_passed > application.lender.sla_days
                    and "notify_OCP"
                    not in overdue_lenders[application.lender.email_group]
                ):
                    current_dt = datetime.now(application.created_at.tzinfo)
                    overdue_lenders[application.lender.email_group]["notify_OCP"] = True
                    application.overdued_at = current_dt

                    message_id = email_utility.send_overdue_application_email_to_OCP(
                        sesClient,
                        application.lender.name,
                    )

                    create_message(
                        application,
                        core.MessageType.OVERDUE_APPLICATION,
                        session,
                        message_id,
                    )

            session.flush()

        for email, lender_data in overdue_lenders.items():
            name = lender_data.get("name")
            count = lender_data.get("count")
            message_id = email_utility.send_overdue_application_email_to_FI(
                sesClient, name, email, count
            )

            create_message(
                application,
                core.MessageType.OVERDUE_APPLICATION,
                session,
                message_id,
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    SLA_overdue_applications()
