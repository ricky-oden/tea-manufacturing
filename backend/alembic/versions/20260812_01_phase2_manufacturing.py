"""phase 2 manufacturing vertical slice

Revision ID: 20260812_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260812_01"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

quantity = sa.Numeric(15, 3)
status = sa.Enum(
    "DRAFT", "ISSUED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="manufacturing_status"
)
inventory_kind = sa.Enum("RAW_MATERIAL", "PRODUCT", name="inventory_kind")
transaction_type = sa.Enum(
    "MANUFACTURING_CONSUMPTION", "MANUFACTURING_OUTPUT", name="inventory_transaction_type"
)


def master_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table("tea_leaves", *master_columns())
    op.create_table("varieties", *master_columns())
    op.create_table("equipment", *master_columns())
    op.create_table(
        "products",
        *master_columns(),
        sa.Column(
            "variety_id",
            sa.BigInteger(),
            sa.ForeignKey("varieties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_table(
        "manufacturing_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_number", sa.String(30), nullable=False, unique=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("planned_quantity", quantity, nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column(
            "equipment_id",
            sa.BigInteger(),
            sa.ForeignKey("equipment.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", status, nullable=False, server_default="DRAFT"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("planned_quantity > 0", name="ck_order_quantity_positive"),
    )
    op.create_table(
        "manufacturing_materials",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "manufacturing_order_id",
            sa.BigInteger(),
            sa.ForeignKey("manufacturing_orders.id", ondelete="CASCADE"),
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
        sa.Column("planned_quantity", quantity, nullable=False),
        sa.CheckConstraint("planned_quantity > 0", name="ck_material_quantity_positive"),
        sa.UniqueConstraint(
            "manufacturing_order_id", "tea_leaf_id", "variety_id", name="uq_order_material"
        ),
    )
    op.create_table(
        "raw_material_inventory_balances",
        sa.Column("id", sa.BigInteger(), primary_key=True),
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
        sa.Column("quantity", quantity, nullable=False, server_default="0.000"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_raw_balance_nonnegative"),
        sa.UniqueConstraint("tea_leaf_id", "variety_id", name="uq_raw_balance_material"),
    )
    op.create_table(
        "product_inventory_balances",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("quantity", quantity, nullable=False, server_default="0.000"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_product_balance_nonnegative"),
    )
    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("inventory_kind", inventory_kind, nullable=False),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("tea_leaf_id", sa.BigInteger(), sa.ForeignKey("tea_leaves.id")),
        sa.Column("variety_id", sa.BigInteger(), sa.ForeignKey("varieties.id")),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id")),
        sa.Column("quantity_delta", quantity, nullable=False),
        sa.Column("balance_after", quantity, nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity_delta <> 0", name="ck_inventory_delta_nonzero"),
        sa.CheckConstraint("balance_after >= 0", name="ck_inventory_balance_after_nonnegative"),
    )
    op.create_index(
        "ix_inventory_transactions_reference",
        "inventory_transactions",
        ["reference_type", "reference_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_reference", table_name="inventory_transactions")
    for table in [
        "inventory_transactions",
        "product_inventory_balances",
        "raw_material_inventory_balances",
        "manufacturing_materials",
        "manufacturing_orders",
        "products",
        "equipment",
        "varieties",
        "tea_leaves",
    ]:
        op.drop_table(table)
    transaction_type.drop(op.get_bind(), checkfirst=True)
    inventory_kind.drop(op.get_bind(), checkfirst=True)
    status.drop(op.get_bind(), checkfirst=True)
