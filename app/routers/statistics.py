import logging
from datetime import datetime, timedelta
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_user
from app.schema import api as ApiSchema

from ..auth import OCP_only
from ..background_processes import statistics_utils
from ..db import get_db
from ..schema import core
from ..schema.core import User
from ..schema.statistic import Statistic, StatisticCustomRange, StatisticType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/statistics-ocp",
    tags=["statistics"],
    response_model=ApiSchema.StatisticResponse,
)
@OCP_only()
async def get_ocp_statistics_by_lender(
    initial_date: Optional[str] = None,
    final_date: Optional[str] = None,
    lender_id: Optional[int] = None,
    custom_range: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Retrieve OCP statistics by lender.

    This secure endpoint is accessible only to users with the OCP role. It retrieves statistics for the Online
    Credit Platform (OCP) based on the specified filters:
    - initial_date (optional): The initial date to filter the statistics.
    - final_date (optional): The final date to filter the statistics.
    - lender_id (optional): The lender ID to filter the statistics for a specific lender.

    :param initial_date: The initial date to filter the statistics (optional).
    :type initial_date: str, optional
    :param final_date: The final date to filter the statistics (optional).
    :type final_date: str, optional
    :param lender_id: The lender ID to filter the statistics for a specific lender (optional).
    :type lender_id: int, optional
    :param current_user: The current user with the OCP role (automatically injected).
    :type current_user: User
    :param session: The database session dependency (automatically injected).
    :type session: Session

    :return: Response containing the OCP statistics.
    :rtype: ApiSchema.StatisticResponse
    """
    try:
        if initial_date is None and final_date is None and custom_range is None:
            # If no dates provided, query the database
            current_date = datetime.now().date()
            statistics_kpis = (
                session.query(Statistic)
                .filter(
                    Statistic.type == StatisticType.APPLICATION_KPIS,
                    Statistic.lender_id == lender_id,
                    func.date(Statistic.created_at) == current_date,
                )
                .first()
            )
            if statistics_kpis is not None:
                statistics_kpis = statistics_kpis.data
            # If no record for the current date, calculate the statistics
            else:
                statistics_kpis = statistics_utils.get_general_statistics(session, initial_date, final_date, lender_id)
        else:
            # If customRange is provided, calculate the statistics based on it
            if custom_range is not None:
                custom_range = custom_range.upper()
                current_date = datetime.now().date()
                if custom_range == StatisticCustomRange.LAST_WEEK.value:
                    initial_date = (current_date - timedelta(days=7)).isoformat()
                elif custom_range == StatisticCustomRange.LAST_MONTH.value:
                    initial_date = (current_date - timedelta(days=30)).isoformat()

                final_date = current_date.isoformat()

            statistics_kpis = statistics_utils.get_general_statistics(session, initial_date, final_date, lender_id)

    except ClientError() as e:
        logger.exception(e)

    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )


@router.get(
    "/statistics-ocp/opt-in",
    tags=["statistics"],
    response_model=ApiSchema.StatisticOptInResponse,
)
@OCP_only()
async def get_ocp_statistics_opt_in(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Retrieve OCP statistics for MSME opt-in.

    This secure endpoint is accessible only to users with the OCP role. It retrieves
    statistics related to MSME opt-in and the count of FIs chosen by MSMEs in the Online Credit Platform (OCP).

    :param current_user: The current user with the OCP role (automatically injected).
    :type current_user: User
    :param session: The database session dependency (automatically injected).
    :type session: Session

    :return: Response containing the OCP statistics for MSME opt-in.
    :rtype: ApiSchema.StatisticOCPResponse
    """
    try:
        current_date = datetime.now().date()
        opt_in_stats = (
            session.query(Statistic)
            .filter(
                and_(
                    Statistic.type == StatisticType.MSME_OPT_IN_STATISTICS,
                    func.date(Statistic.created_at) == current_date,
                )
            )
            .first()
        )
        if opt_in_stats is not None:
            opt_in_stats = opt_in_stats.data
        else:
            opt_in_stats = statistics_utils.get_msme_opt_in_stats(session)

    except ClientError as e:
        logger.exception(e)
    return ApiSchema.StatisticOptInResponse(
        opt_in_stat=opt_in_stats,
    )


@router.get("/statistics-fi", tags=["statistics"], response_model=ApiSchema.StatisticResponse)
async def get_fi_statistics(session: Session = Depends(get_db), user: core.User = Depends(get_user)):
    """
    Retrieve statistics for a Financial Institution (FI).

    This endpoint retrieves statistics specific to a Financial Institution (FI).
    It provides general statistics such as the number of applications, awards, and borrowers
    associated with the FI.

    :param session: The database session dependency (automatically injected).
    :type session: Session
    :param user: The current user (automatically injected).
    :type user: core.User

    :return: Response containing the statistics for the Financial Institution.
    :rtype: ApiSchema.StatisticResponse
    """
    try:
        current_date = datetime.now().date()

        statistics_kpis = (
            session.query(Statistic)
            .filter(
                and_(
                    Statistic.type == StatisticType.APPLICATION_KPIS,
                    Statistic.lender_id == user.lender_id,
                    func.date(Statistic.created_at) == current_date,
                )
            )
            .first()
        )
        if statistics_kpis is not None:
            statistics_kpis = statistics_kpis.data
        else:
            statistics_kpis = statistics_utils.get_general_statistics(session, None, None, user.lender_id)

    except ClientError as e:
        logger.exception(e)

    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )
