from pydantic import BaseModel

from app.schema.core import Application, Award, Borrower


class ApplicationResponse(BaseModel):
    application: Application
    borrower: Borrower
    award: Award


class ApplicationDeclinePayload(BaseModel):
    declineThis: bool
    declineAll: bool


class ApplicationDeclineFeedbackPayload(BaseModel):
    declineThis: bool


#         dontNeedAccessCredit: boolean(),
# alreadyHaveAcredit: boolean(),
# prefferToGoToBank: boolean(),
# dontWantAccessCredit: boolean(),
# other: boolean(),
# otherCommnets: string(),
