from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

QUANTITY_TYPE = Numeric(15, 3)


class ManufacturingStatus(StrEnum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InventoryKind(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PRODUCT = "PRODUCT"


class InventoryTransactionType(StrEnum):
    MANUFACTURING_CONSUMPTION = "MANUFACTURING_CONSUMPTION"
    MANUFACTURING_OUTPUT = "MANUFACTURING_OUTPUT"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MasterMixin(TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class TeaLeaf(MasterMixin, Base):
    __tablename__ = "tea_leaves"


class Variety(MasterMixin, Base):
    __tablename__ = "varieties"


class Equipment(MasterMixin, Base):
    __tablename__ = "equipment"


class Product(MasterMixin, Base):
    __tablename__ = "products"

    variety_id: Mapped[int] = mapped_column(ForeignKey("varieties.id", ondelete="RESTRICT"))
    variety: Mapped[Variety] = relationship()


class ManufacturingOrder(TimestampMixin, Base):
    __tablename__ = "manufacturing_orders"
    __table_args__ = (CheckConstraint("planned_quantity > 0", name="ck_order_quantity_positive"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    planned_quantity: Mapped[Decimal] = mapped_column(QUANTITY_TYPE)
    planned_date: Mapped[date] = mapped_column(Date)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="RESTRICT"))
    status: Mapped[ManufacturingStatus] = mapped_column(
        Enum(ManufacturingStatus, name="manufacturing_status"),
        default=ManufacturingStatus.DRAFT,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    product: Mapped[Product] = relationship()
    equipment: Mapped[Equipment] = relationship()
    materials: Mapped[list["ManufacturingMaterial"]] = relationship(
        cascade="all, delete-orphan", order_by="ManufacturingMaterial.id"
    )


class ManufacturingMaterial(Base):
    __tablename__ = "manufacturing_materials"
    __table_args__ = (
        CheckConstraint("planned_quantity > 0", name="ck_material_quantity_positive"),
        UniqueConstraint(
            "manufacturing_order_id", "tea_leaf_id", "variety_id", name="uq_order_material"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    manufacturing_order_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturing_orders.id", ondelete="CASCADE")
    )
    tea_leaf_id: Mapped[int] = mapped_column(ForeignKey("tea_leaves.id", ondelete="RESTRICT"))
    variety_id: Mapped[int] = mapped_column(ForeignKey("varieties.id", ondelete="RESTRICT"))
    planned_quantity: Mapped[Decimal] = mapped_column(QUANTITY_TYPE)
    tea_leaf: Mapped[TeaLeaf] = relationship()
    variety: Mapped[Variety] = relationship()


class RawMaterialInventoryBalance(TimestampMixin, Base):
    __tablename__ = "raw_material_inventory_balances"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_raw_balance_nonnegative"),
        UniqueConstraint("tea_leaf_id", "variety_id", name="uq_raw_balance_material"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tea_leaf_id: Mapped[int] = mapped_column(ForeignKey("tea_leaves.id", ondelete="RESTRICT"))
    variety_id: Mapped[int] = mapped_column(ForeignKey("varieties.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY_TYPE, default=Decimal("0.000"))


class ProductInventoryBalance(TimestampMixin, Base):
    __tablename__ = "product_inventory_balances"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_product_balance_nonnegative"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), unique=True
    )
    quantity: Mapped[Decimal] = mapped_column(QUANTITY_TYPE, default=Decimal("0.000"))


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint("quantity_delta <> 0", name="ck_inventory_delta_nonzero"),
        CheckConstraint("balance_after >= 0", name="ck_inventory_balance_after_nonnegative"),
        Index("ix_inventory_transactions_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    inventory_kind: Mapped[InventoryKind] = mapped_column(
        Enum(InventoryKind, name="inventory_kind")
    )
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(
        Enum(InventoryTransactionType, name="inventory_transaction_type")
    )
    tea_leaf_id: Mapped[int | None] = mapped_column(ForeignKey("tea_leaves.id"))
    variety_id: Mapped[int | None] = mapped_column(ForeignKey("varieties.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    quantity_delta: Mapped[Decimal] = mapped_column(QUANTITY_TYPE)
    balance_after: Mapped[Decimal] = mapped_column(QUANTITY_TYPE)
    reference_type: Mapped[str] = mapped_column(String(50))
    reference_id: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
