import logging
from datetime import datetime, timedelta
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.schema import api as ApiSchema
from app.utils.verify_token import get_current_user, get_user

from ..background_processes import statistics_utils
from ..db.session import get_db
from ..schema import core
from ..schema.core import User
from ..schema.statistic import Statistic, StatisticCustomRange, StatisticType
from ..utils.permissions import OCP_only

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
    try:
        if initial_date is None and final_date is None and custom_range is None:
            logging.info(
                "Queriying OCP general statistics data from DB for lender "
                + str(lender_id)
                + " between dates "
                + (
                    initial_date
                    if initial_date
                    else "not provided"
                    + " and "
                    + (final_date if final_date else "not provided")
                )
            )
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
            # If no record for the current date, calculate the statistics
            if statistics_kpis is None:
                logging.info(
                    "no records found for the current date, next step is to calculate the statistics"
                )
                statistics_kpis = statistics_utils.get_general_statistics(
                    session, initial_date, final_date, lender_id
                )
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

            statistics_kpis = statistics_utils.get_general_statistics(
                session, initial_date, final_date, lender_id
            )

    except ClientError as e:
        logging.error(e)

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
    try:
        current_date = datetime.now().date()
        logging.info("Queriying opt in stats data from DB")
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

        if opt_in_stats is None:
            logging.info(
                "no records found for the current date, next step is to calculate the statistics"
            )
            opt_in_stats = statistics_utils.get_msme_opt_in_stats(session)

    except ClientError as e:
        logging.error(e)
    logging.info(opt_in_stats)
    return ApiSchema.StatisticOptInResponse(
        opt_in_stat=opt_in_stats,
    )


@router.get(
    "/statistics-fi", tags=["statistics"], response_model=ApiSchema.StatisticResponse
)
async def get_fi_statistics(
    session: Session = Depends(get_db), user: core.User = Depends(get_user)
):
    try:
        current_date = datetime.now().date()
        logging.info(
            "Queriying FI general statistics data from DB for lender "
            + str(user.lender_id)
        )

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

        if statistics_kpis is None:
            logging.info(
                "no records found for the current date, next step is to calculate the statistics"
            )
            statistics_kpis = statistics_utils.get_general_statistics(
                session, None, None, user.lender_id
            )

    except ClientError as e:
        logging.error(e)

    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )
