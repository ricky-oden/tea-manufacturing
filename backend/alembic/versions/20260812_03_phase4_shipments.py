"""phase 4 shipments

Revision ID: 20260812_03
Revises: 20260812_02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260812_03"
down_revision: str | None = "20260812_02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

quantity = sa.Numeric(15, 3)
shipment_status = sa.Enum("DRAFT", "CONFIRMED", name="shipment_status")


def upgrade() -> None:
    op.execute("ALTER TYPE inventory_transaction_type ADD VALUE IF NOT EXISTS 'SHIPMENT'")
    op.create_table(
        "shipments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("shipment_number", sa.String(30), nullable=False, unique=True),
        sa.Column("shipped_date", sa.Date(), nullable=False),
        sa.Column("status", shipment_status, nullable=False, server_default="DRAFT"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "shipment_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "shipment_id",
            sa.BigInteger(),
            sa.ForeignKey("shipments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", quantity, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_shipment_line_quantity_positive"),
        sa.UniqueConstraint("shipment_id", "product_id", name="uq_shipment_product"),
    )


def downgrade() -> None:
    op.drop_table("shipment_lines")
    op.drop_table("shipments")
    shipment_status.drop(op.get_bind(), checkfirst=True)
    # PostgreSQL enum values are intentionally retained during downgrade.
