from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder


def update_models(payload, model):
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        setattr(model, field, value)


def update_models_with_validation(payload, model):
    update_dict = jsonable_encoder(payload, exclude_unset=True)
    for field, value in update_dict.items():
        if model.missing_data[field]:
            setattr(model, field, value)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This column cannot be updated",
            )
