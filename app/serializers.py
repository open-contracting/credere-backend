from typing import Any

from pydantic import BaseModel, Field

from app import models


class ApplicationResponse(BaseModel):
    application: models.ApplicationRead
    borrower: models.Borrower
    award: models.Award
    lender: models.Lender | None = None
    documents: list[models.BorrowerDocumentBase] = Field(default_factory=list)
    creditProduct: models.CreditProduct | None = None


class CreditProductListResponse(BaseModel):
    loans: list[models.CreditProductWithLender]
    credit_lines: list[models.CreditProductWithLender]


class BasePagination(BaseModel):
    count: int
    page: int
    page_size: int


class ApplicationListResponse(BasePagination):
    items: list[models.ApplicationWithRelations]


class LenderListResponse(BasePagination):
    items: list[models.Lender]


class UserListResponse(BasePagination):
    items: list[models.UserWithLender]


class ResponseBase(BaseModel):
    detail: str


class ChangePasswordResponse(ResponseBase):
    secret_code: str
    session: str
    username: str


class UserResponse(BaseModel):
    user: models.User


class LoginResponse(UserResponse):
    access_token: str
    refresh_token: str


class StatisticResponse(BaseModel):
    statistics_kpis: dict[Any, Any]


class StatisticData(BaseModel):
    name: str
    value: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


class StatisticOptInResponse(BaseModel):
    opt_in_stat: dict[Any, Any]
