# Credere frontend schema are in comments.

from typing import Any

from pydantic import BaseModel, Field

from app import models


class ApplicationResponse(BaseModel):
    application: models.ApplicationRead  # IApplication
    borrower: models.Borrower  # IBorrower
    award: models.Award  # IAward
    lender: models.Lender | None = None  # ILender
    documents: list[models.BorrowerDocumentBase] = Field(default_factory=list)  # IBorrowerDocument
    creditProduct: models.CreditProduct | None = None  # ICreditProduct # noqa: N815 # backwards-compatibility


class CreditProductListResponse(BaseModel):
    loans: list[models.CreditProductWithLender]  # ICreditProduct
    credit_lines: list[models.CreditProductWithLender]  # ICreditProduct


# Abtract
class BasePagination(BaseModel):
    count: int
    page: int
    page_size: int


class ApplicationListResponse(BasePagination):
    items: list[models.ApplicationWithRelations]  # IApplication


class LenderListResponse(BasePagination):
    items: list[models.Lender]  # ILender


class UserListResponse(BasePagination):
    items: list[models.UserWithLender]  # IUser


class ResponseBase(BaseModel):
    detail: str


class ChangePasswordResponse(ResponseBase):
    secret_code: str
    session: str
    username: str


class UserResponse(BaseModel):
    user: models.User  # IUser


class LoginResponse(UserResponse):
    access_token: str
    refresh_token: str


class StatisticResponse(BaseModel):
    statistics_kpis: dict[Any, Any]  # StatisticsKpis


class StatisticData(BaseModel):  # ChartData
    name: str
    value: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


class StatisticOptInResponse(BaseModel):
    opt_in_stat: dict[Any, Any]  # OptInStat
