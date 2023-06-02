def create_application(
    award_id, borrower_id, email, legal_identifier, source_contract_id
):
    application = {
        "award_id": award_id,
        "borrower_id": borrower_id,
        "primary_email": email,
    }
    return application
