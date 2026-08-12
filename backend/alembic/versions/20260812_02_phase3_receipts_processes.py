"""phase 3 receipts processes and suppliers

Revision ID: 20260812_02
Revises: 20260812_01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260812_02"
down_revision: str | None = "20260812_01"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

quantity = sa.Numeric(15, 3)
process_status = sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", name="process_status")


def upgrade() -> None:
    op.execute("ALTER TYPE inventory_transaction_type ADD VALUE IF NOT EXISTS 'RECEIPT'")
    op.create_table(
        "suppliers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "raw_material_receipts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("receipt_number", sa.String(30), nullable=False, unique=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column(
            "supplier_id",
            sa.BigInteger(),
            sa.ForeignKey("suppliers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "raw_material_receipt_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "receipt_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_material_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tea_leaf_id",
            sa.BigInteger(),
            sa.ForeignKey("tea_leaves.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "variety_id",
            sa.BigInteger(),
            sa.ForeignKey("varieties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", quantity, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_receipt_line_quantity_positive"),
    )
    op.create_table(
        "manufacturing_processes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "manufacturing_order_id",
            sa.BigInteger(),
            sa.ForeignKey("manufacturing_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("process_code", sa.String(30), nullable=False),
        sa.Column("process_name", sa.String(100), nullable=False),
        sa.Column("status", process_status, nullable=False, server_default="PENDING"),
        sa.Column(
            "equipment_id",
            sa.BigInteger(),
            sa.ForeignKey("equipment.id", ondelete="RESTRICT"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("result_note", sa.String(500)),
        sa.CheckConstraint("sequence > 0", name="ck_process_sequence_positive"),
        sa.UniqueConstraint("manufacturing_order_id", "sequence", name="uq_order_process_sequence"),
        sa.UniqueConstraint("manufacturing_order_id", "process_code", name="uq_order_process_code"),
    )


def downgrade() -> None:
    op.drop_table("manufacturing_processes")
    process_status.drop(op.get_bind(), checkfirst=True)
    op.drop_table("raw_material_receipt_lines")
    op.drop_table("raw_material_receipts")
    op.drop_table("suppliers")
    # PostgreSQL enum values are intentionally retained during downgrade.
