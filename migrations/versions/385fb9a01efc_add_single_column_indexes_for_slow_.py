"""Add single-column indexes for slow queries

Revision ID: 385fb9a01efc
Revises: 55ef2bbbfcba
Create Date: 2023-10-23 12:32:30.252552

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "385fb9a01efc"
down_revision = "55ef2bbbfcba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_application_uuid", table_name="application")
    op.create_index(
        op.f("ix_application_award_id"), "application", ["award_id"], unique=False
    )
    op.create_index(
        op.f("ix_application_borrower_id"), "application", ["borrower_id"], unique=False
    )
    op.create_index(
        op.f("ix_application_confirmation_email_token"),
        "application",
        ["confirmation_email_token"],
        unique=False,
    )
    op.create_unique_constraint(None, "application", ["uuid"])
    op.create_index(
        op.f("ix_award_source_contract_id"),
        "award",
        ["source_contract_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credere_user_external_id"),
        "credere_user",
        ["external_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credit_product_lender_id"),
        "credit_product",
        ["lender_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_credit_product_lender_id"), table_name="credit_product")
    op.drop_index(op.f("ix_credere_user_external_id"), table_name="credere_user")
    op.drop_index(op.f("ix_award_source_contract_id"), table_name="award")
    op.drop_constraint(None, "application", type_="unique")
    op.drop_index(
        op.f("ix_application_confirmation_email_token"), table_name="application"
    )
    op.drop_index(op.f("ix_application_borrower_id"), table_name="application")
    op.drop_index(op.f("ix_application_award_id"), table_name="application")
    op.create_index("ix_application_uuid", "application", ["uuid"], unique=False)
    # ### end Alembic commands ###
