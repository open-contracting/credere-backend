from app import models

FI_user = {
    "email": "FI_user@noreply.open-contracting.org",
    "name": "Test FI",
    "type": models.UserType.FI,
}

FI_user_with_lender = {
    "email": "FI_user_with_lender@noreply.open-contracting.org",
    "name": "Test FI with lender",
    "type": models.UserType.FI,
    "lender_id": 1,
}

OCP_user = {
    "email": "OCP_user@noreply.open-contracting.org",
    "name": "OCP_user@example.com",
    "type": models.UserType.OCP,
}
