from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app import models


class ApplicationResponse(BaseModel):
    application: models.ApplicationRead
    borrower: models.Borrower
    award: models.Award
    lender: Optional[models.Lender] = None
    documents: List[models.BorrowerDocumentBase] = []
    creditProduct: Optional[models.CreditProduct] = None


class CreditProductListResponse(BaseModel):
    loans: List[models.CreditProductWithLender]
    credit_lines: List[models.CreditProductWithLender]


class BasePagination(BaseModel):
    count: int
    page: int
    page_size: int


class ApplicationListResponse(BasePagination):
    items: List[models.ApplicationWithRelations]


class LenderListResponse(BasePagination):
    items: List[models.Lender]


class UserListResponse(BasePagination):
    items: List[models.UserWithLender]


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
    statistics_kpis: Dict[Any, Any]


class StatisticOptInResponse(BaseModel):
    opt_in_stat: Dict[Any, Any]
