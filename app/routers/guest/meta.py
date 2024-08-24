from fastapi import APIRouter

from app import models
from app.i18n import _

router = APIRouter()


@router.get(
    "/meta",
    tags=["meta"],
)
async def get_settings_by_domain() -> dict[str, list[dict[str, str]]]:
    """
    Get the keys and localized descriptions of constants, where a constant can be:

        - BorrowerDocumentType
        - BorrowerSector
        - BorrowerSize
        - BorrowerType

    :return: A dict of constants with their keys and localized values.
    """
    constants = {}
    for domain in (
        "BorrowerDocumentType",
        "BorrowerSector",
        "BorrowerSize",
        "BorrowerType",
    ):
        constants[domain] = [{"label": _(name), "value": name} for name in getattr(models, domain)]
    return constants
