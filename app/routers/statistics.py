import logging
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schema import api as ApiSchema
from app.utils.verify_token import get_current_user, get_user

from ..background_processes import statistics_utils
from ..db.session import get_db
from ..schema import core
from ..schema.core import User
from ..utils.permissions import OCP_only

router = APIRouter()


@router.get(
    "/statistics-ocp",
    tags=["statistics"],
    response_model=ApiSchema.StatisticResponse,
)
@OCP_only()
async def get_ocp_statistics_by_lender(
    initialDate: Optional[str] = None,
    finalDate: Optional[str] = None,
    lender: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    try:
        statistics_kpis = statistics_utils.get_general_statistics(
            session, initialDate, finalDate, lender
        )

    except ClientError as e:
        logging.error(e)

    return ApiSchema.StatisticResponse(
        statistics_kpis=statistics_kpis,
    )


@router.get(
    "/statistics-ocp/opt-in",
    tags=["statistics"],
    response_model=ApiSchema.StatisticOCPResponse,
)
@OCP_only()
async def get_ocp_statistics_opt_in(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    try:
        opt_in_stats = statistics_utils.get_msme_opt_in_stats(session)
        fis_choosen_by_msme = statistics_utils.get_count_of_fis_choosen_by_msme(session)
        proportion_of_submited_out_of_opt_in = (
            statistics_utils.get_proportion_of_submited_out_of_opt_in(session)
        )
    except ClientError as e:
        logging.error(e)

    return ApiSchema.StatisticOCPResponse(
        opt_in_stat=opt_in_stats,
        fis_choosen_by_msme=fis_choosen_by_msme,
        proportion_of_submited_out_of_opt_in=proportion_of_submited_out_of_opt_in,
    )


@router.get(
    "/statistics-fi", tags=["statistics"], response_model=ApiSchema.StatisticFIResponse
)
async def get_fi_statistics(
    session: Session = Depends(get_db), user: core.User = Depends(get_user)
):
    try:
        statistics_kpis = statistics_utils.get_general_statistics(
            session, None, None, user.lender_id
        )
        proportion_of_msme_selecting_current_fi = (
            statistics_utils.get_proportion_of_msme_selecting_current_fi(
                session, user.lender_id
            )
        )
    except ClientError as e:
        logging.error(e)
    return ApiSchema.StatisticFIResponse(
        statistics_kpis=statistics_kpis,
        proportion_of_msme_selecting_current_fi=proportion_of_msme_selecting_current_fi,
    )
