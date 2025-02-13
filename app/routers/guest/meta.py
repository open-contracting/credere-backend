from fastapi import APIRouter

from app import models, util
from app.i18n import _

router = APIRouter()


@router.get(
    "/meta",
    tags=[util.Tags.meta],
)
async def get_settings_by_domain() -> dict[str, list[dict[str, str]]]:
    """
    Get the keys and localized descriptions of constants.

    A constant can be:
    - ApplicationStatus
    - BorrowerDocumentType
    - BorrowerSector
    - BorrowerSize
    - BorrowerType

    :return: A dict of constants with their keys and localized values.
    """
    constants = {}
    for domain in (
        "ApplicationStatus",
        "BorrowerDocumentType",
        "BorrowerSector",
        "BorrowerSize",
        "BorrowerType",
    ):
        constants[domain] = [{"label": _(name), "value": name} for name in getattr(models, domain)]
    return constants
