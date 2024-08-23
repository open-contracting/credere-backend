from fastapi import APIRouter, HTTPException, status

from app import models
from app.i18n import _

router = APIRouter()


@router.get(
    "/meta/{domain}",
    tags=["meta"],
)
async def get_settings_by_domain(domain: str) -> list[dict[str, str]]:
    """
    Get the keys and localized descriptions of a specific domain, where a domain can be:

        - BorrowerDocumentType
        - BorrowerSector
        - BorrowerSize
        - BorrowerType
        - CreditType

    :return: A dict of the domain key and localized value.
    """
    if domain not in (
        "BorrowerDocumentType",
        "BorrowerSector",
        "BorrowerSize",
        "BorrowerType",
        "CreditType",
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_("Domain doesn't exist"),
        )
    return [{"label": _(name), "value": name} for name in getattr(models, domain)]
