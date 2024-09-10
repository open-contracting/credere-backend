from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.utils.statistics as statistics_utils
from app import dependencies, serializers
from app.db import get_db
from app.models import User
from app.util import StatisticCustomRange

router = APIRouter()


@router.get(
    "/statistics-ocp",
    tags=["statistics"],
)
async def get_admin_statistics_by_lender(
    initial_date: str | None = None,
    final_date: str | None = None,
    lender_id: int | None = None,
    custom_range: StatisticCustomRange | None = None,
    admin: User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> serializers.StatisticResponse:
    """
    Retrieve OCP statistics by lender.

    This secure endpoint is accessible only to users with the OCP role. It retrieves statistics for admins
    based on the specified filters:
    - initial_date (optional): The initial date to filter the statistics.
    - final_date (optional): The final date to filter the statistics.
    - lender_id (optional): The lender ID to filter the statistics for a specific lender.

    :param initial_date: The initial date to filter the statistics (optional).
    :param final_date: The final date to filter the statistics (optional).
    :param lender_id: The lender ID to filter the statistics for a specific lender (optional).
    :return: Response containing the admin statistics.
    """

    if initial_date is None and final_date is None and custom_range is None:
        statistics_kpis = statistics_utils.get_general_statistics(session, initial_date, final_date, lender_id)
    else:
        if custom_range is not None:
            custom_range = custom_range.upper()
            current_date = datetime.now().date()

            if custom_range == StatisticCustomRange.LAST_WEEK:
                initial_date = (current_date - timedelta(days=7)).isoformat()
            elif custom_range == StatisticCustomRange.LAST_MONTH:
                initial_date = (current_date - timedelta(days=30)).isoformat()
            final_date = current_date.isoformat()

        statistics_kpis = statistics_utils.get_general_statistics(session, initial_date, final_date, lender_id)

    return serializers.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )


@router.get(
    "/statistics-ocp/opt-in",
    tags=["statistics"],
)
async def get_admin_statistics_opt_in(
    admin: User = Depends(dependencies.get_admin_user),
    session: Session = Depends(get_db),
) -> serializers.StatisticOptInResponse:
    """
    Retrieve OCP statistics for borrower opt-in.

    This secure endpoint is accessible only to users with the admin role. It retrieves
    statistics related to borrower opt-in and the count of lenders chosen by borrower.

    :return: Response containing the admin statistics for borrower opt-in.
    """

    return serializers.StatisticOptInResponse(
        opt_in_stat=statistics_utils.get_borrower_opt_in_stats(session),
    )


@router.get(
    "/statistics-fi",
    tags=["statistics"],
)
async def get_lender_statistics(
    session: Session = Depends(get_db),
    user: User = Depends(dependencies.get_user),
) -> serializers.StatisticResponse:
    """
    Retrieve statistics for a lender.

    This endpoint retrieves statistics specific to a lender.
    It provides general statistics such as the number of applications, awards, and borrowers
    associated with the lender.

    :return: Response containing the statistics for the lender.
    """

    return serializers.StatisticResponse(
        statistics_kpis=statistics_utils.get_general_statistics(session, None, None, user.lender_id),
    )
