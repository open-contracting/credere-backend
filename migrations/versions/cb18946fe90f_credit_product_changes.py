"""credit product changes

Revision ID: cb18946fe90f
Revises: 173969eb685c
Create Date: 2023-06-30 18:41:50.617613

"""
import sqlalchemy as sa
import sqlmodel  # added
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cb18946fe90f"
down_revision = "8ab95d68febd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "credit_product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "borrower_size",
            postgresql.ENUM(name="borrower_size", create_type=False),
            nullable=False,
        ),
        sa.Column("lower_limit", sa.DECIMAL(precision=16, scale=2), nullable=False),
        sa.Column("upper_limit", sa.DECIMAL(precision=16, scale=2), nullable=False),
        sa.Column("interest_rate", sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column(
            "type", sa.Enum("LOAN", "CREDIT_LINE", name="credit_type"), nullable=False
        ),
        sa.Column(
            "required_document_types",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "other_fees_total_amount", sa.DECIMAL(precision=16, scale=2), nullable=False
        ),
        sa.Column(
            "other_fees_description", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("more_info_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("lender_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["lender_id"],
            ["lender.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "application", sa.Column("credit_product_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        None, "application", "credit_product", ["credit_product_id"], ["id"]
    )
    op.drop_column("lender", "borrower_type_preferences")
    op.drop_column("lender", "limits_preferences")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "lender",
        sa.Column(
            "limits_preferences",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "lender",
        sa.Column(
            "borrower_type_preferences",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_column("application", "credit_product_id")
    op.drop_table("credit_product")
    op.execute("DROP TYPE credit_type")
    # ### end Alembic commands ###