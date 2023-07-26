import re

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder


def update_models(payload, model):
    """
    Update a model with given payload:
    This function encodes the payload to a dictionary and sets the model's attributes.

    :param payload: The payload to encode and update the model.
    :type payload: Usually a Pydantic model or any other Python object.

    :param model: The model to update.
    :type model: Usually a SQLAlchemy model or any other Python object.

    :return: None. The model is updated in-place.
    """
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        setattr(model, field, value)


def update_models_with_validation(payload, model):
    """
    Update a model with validation:
    This function encodes the payload to a dictionary and sets the model's attributes
    after checking the `missing_data` attribute of the model for the corresponding field.

    :param payload: The payload to encode and update the model.
    :type payload: Usually a Pydantic model or any other Python object.

    :param model: The model to update.
    :type model: Usually a SQLAlchemy model or any other Python object.

    :return: None. The model is updated in-place.

    :raises HTTPException: If a field that is not missing data is attempted to be updated.
    """
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        if model.missing_data[field]:
            setattr(model, field, value)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This column cannot be updated",
            )


def sentry_filter_transactions(event, hint):
    """
    Filter transactions to be sent to Sentry.
    This function prevents transactions that interact with AWS Cognito from being sent to Sentry.

    :param event: The event data.
    :type event: dict

    :param hint: A dictionary of extra data passed to the function.
    :type hint: dict

    :return: The event data if it should be sent to Sentry, otherwise None.
    :rtype: dict or None
    """
    data_url = event["breadcrumbs"]["values"][0]["data"]["url"] or None
    if data_url and re.search(r"https://cognito-idp.*\.amazonaws\.com", data_url):
        return None

    return event
