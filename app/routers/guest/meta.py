from typing import Any

from fastapi import APIRouter, HTTPException, status

from app import models
from app.i18n import _

router = APIRouter()


@router.get(
    "/meta/{domain}",
    tags=["meta"],
)
async def get_settings_by_domain(domain: str) -> list[dict[str, str | Any]]:
    """
    Get the keys and localized descriptions of a specific domain, where a domain can be:
        - BorrowerType
        - CreditType
        - BorrowerDocumentType
        - BorrowerSize
        - BorrowerSector,

    :return: A dict of the domain key and localized value.
    """
    if domain not in [
        "BorrowerType",
        "CreditType",
        "BorrowerDocumentType",
        "BorrowerSize",
        "BorrowerSector",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_("Domain doesn't exist"),
        )
    return [{"label": _(name), "value": name} for name in getattr(models, domain)]
