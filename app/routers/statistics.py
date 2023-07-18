import logging
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schema import api as ApiSchema
from app.utils.verify_token import get_current_user, get_user

from ..background_processes import statistics_utils
from ..db.session import get_db
from ..schema import core
from ..schema.core import User
from ..schema.statistic import Statistic, StatisticType
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
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    try:
        # Hacer consulta a la BD del APPLICATION_KPIS,
        # cual es la ultima fecha, si no es hoy calcula, si es hoy enviar lo obtenido de la BD

        statistics_kpis = statistics_utils.get_general_statistics(
            session, initial_date, final_date, lender_id
        )

    except ClientError as e:
        logging.error(e)

    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )


@router.get(
    "/db_statistics-ocp",
    tags=["statistics"],
    response_model=ApiSchema.StatisticResponse,
)
@OCP_only()
async def get_db_ocp_statistics_by_lender(
    initialDate: Optional[str] = None,
    finalDate: Optional[str] = None,
    lender: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    # Add code to query APPLICATION_KPIS
    statistics_kpis = (
        session.query(Statistic)
        .filter(
            Statistic.type == StatisticType.APPLICATION_KPIS,
            Statistic.lender_id == lender,  # assuming lender is the lender_id
        )
        .first()
    )

    if statistics_kpis is None:
        raise HTTPException(status_code=404, detail="Statistic not found")
    else:
        return ApiSchema.StatisticResponse(
            statistics_kpis=statistics_kpis.data,
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
        opt_in_stats = statistics_utils.get_msme_opt_in_stats(session)
    except ClientError as e:
        logging.error(e)

    return ApiSchema.StatisticOptInResponse(
        opt_in_stat=opt_in_stats,
    )


@router.get(
    "/db_statistics-ocp/opt-in",
    tags=["statistics"],
    response_model=ApiSchema.StatisticOptInResponse,
)
@OCP_only()
async def get_db_ocp_statistics_opt_in(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    statistics_opt_in = (
        session.query(Statistic)
        .filter(
            Statistic.type == StatisticType.MSME_OPT_IN_STATISTICS,
        )
        .first()
    )

    if statistics_opt_in is None:
        raise HTTPException(status_code=404, detail="Statistic not found")
    else:
        return ApiSchema.StatisticOptInResponse(
            opt_in_stat=statistics_opt_in.data,
        )


@router.get(
    "/statistics-fi", tags=["statistics"], response_model=ApiSchema.StatisticResponse
)
async def get_fi_statistics(
    session: Session = Depends(get_db), user: core.User = Depends(get_user)
):
    try:
        statistics_kpis = statistics_utils.get_general_statistics(
            session, None, None, user.lender_id
        )
    except ClientError as e:
        logging.error(e)
    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )
