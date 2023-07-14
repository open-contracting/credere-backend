import logging
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.utils.verify_token import get_current_user, get_user

from ..background_processes import statistics_utils
from ..db.session import get_db
from ..schema import core
from ..schema.core import User
from ..utils.permissions import OCP_only

router = APIRouter()


# this need to receive dates, and may o may not receive a lender
# as this is get, the dates should be in the url as query params
# after the test i need to add the OCP only decorator
@router.get("/statistics-ocp")
@OCP_only()
async def get_calculated_ocp_statistics(
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
        opt_in_stats = statistics_utils.get_msme_opt_in_stats(session)
        msme_opt_in = statistics_utils.get_msme_opt_in_stats(session)
        fis_choosen_by_msme = statistics_utils.get_count_of_fis_choosen_by_msme(session)
        proportion_of_submited_out_of_opt_in = (
            statistics_utils.get_proportion_of_submited_out_of_opt_in(session)
        )
    except ClientError as e:
        logging.error(e)
    return (
        statistics_kpis,
        opt_in_stats,
        msme_opt_in,
        fis_choosen_by_msme,
        proportion_of_submited_out_of_opt_in,
    )
    # return ApiSchema.ResponseBase(detail=result)


@router.get("/statistics-fi")
async def get_calculated_fi_statistics(
    session: Session = Depends(get_db), user: core.User = Depends(get_user)
):
    try:
        lender = user.lender_id
        print(lender)
        statistics_kpis = statistics_utils.get_general_statistics(
            session, None, None, lender
        )
        proportion_of_msme_selecting_current_fi = (
            statistics_utils.get_proportion_of_msme_selecting_current_fi(
                session, lender
            )
        )
    except ClientError as e:
        logging.error(e)
    return (statistics_kpis, proportion_of_msme_selecting_current_fi)
