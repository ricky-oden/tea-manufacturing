from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.models.manufacturing import (
    InventoryKind,
    InventoryTransactionType,
    ManufacturingStatus,
    ShipmentStatus,
)
from app.schemas.manufacturing import Quantity


class ShipmentLineInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Quantity


class ShipmentWrite(BaseModel):
    shipment_number: str = Field(min_length=1, max_length=30)
    shipped_date: date
    lines: list[ShipmentLineInput] = Field(min_length=1)

    @model_validator(mode="after")
    def products_are_unique(self):
        product_ids = [line.product_id for line in self.lines]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("同じ製品を重複指定できません。")
        return self


class ShipmentLineResponse(ShipmentLineInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_code: str
    product_name: str

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ShipmentResponse(BaseModel):
    id: int
    shipment_number: str
    shipped_date: date
    status: ShipmentStatus
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[ShipmentLineResponse]


class ShipmentListResponse(BaseModel):
    items: list[ShipmentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class RawBalanceResponse(BaseModel):
    id: int
    tea_leaf_id: int
    tea_leaf_code: str
    tea_leaf_name: str
    variety_id: int
    variety_code: str
    variety_name: str
    quantity: Decimal
    unit: str = "kg"
    updated_at: datetime

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ProductBalanceResponse(BaseModel):
    id: int
    product_id: int
    product_code: str
    product_name: str
    quantity: Decimal
    unit: str = "kg"
    updated_at: datetime

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class InventoryTransactionResponse(BaseModel):
    id: int
    inventory_kind: InventoryKind
    transaction_type: InventoryTransactionType
    tea_leaf_id: int | None
    variety_id: int | None
    product_id: int | None
    target_code: str
    target_name: str
    quantity_delta: Decimal
    balance_after: Decimal
    unit: str = "kg"
    reference_type: str
    reference_id: int
    occurred_at: datetime

    @field_serializer("quantity_delta", "balance_after", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class PageResponse(BaseModel):
    items: list
    page: int
    page_size: int
    total: int
    total_pages: int


class BreakdownItem(BaseModel):
    code: str
    name: str
    quantity: Decimal

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class SummaryResponse(BaseModel):
    date_from: date
    date_to: date
    receipt_quantity: Decimal
    manufacturing_quantity: Decimal
    shipment_quantity: Decimal
    current_raw_material_quantity: Decimal
    current_product_quantity: Decimal
    receipt_breakdown: list[BreakdownItem]
    manufacturing_breakdown: list[BreakdownItem]
    shipment_breakdown: list[BreakdownItem]

    @field_serializer(
        "receipt_quantity",
        "manufacturing_quantity",
        "shipment_quantity",
        "current_raw_material_quantity",
        "current_product_quantity",
        when_used="json",
    )
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class InventoryOverview(BaseModel):
    item_count: int
    total_quantity: Decimal
    unit: str = "kg"

    @field_serializer("total_quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class DashboardResponse(BaseModel):
    date_from: date
    date_to: date
    manufacturing_status_counts: dict[ManufacturingStatus, int]
    raw_material_inventory: InventoryOverview
    product_inventory: InventoryOverview
    receipt_quantity: Decimal
    manufacturing_quantity: Decimal
    shipment_quantity: Decimal

    @field_serializer(
        "receipt_quantity", "manufacturing_quantity", "shipment_quantity", when_used="json"
    )
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)
