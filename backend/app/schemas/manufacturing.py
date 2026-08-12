from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.manufacturing import (
    InventoryKind,
    InventoryTransactionType,
    ManufacturingStatus,
    ProcessStatus,
)

Quantity = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=3)]


class MasterCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class ProductCreate(MasterCreate):
    variety_id: int = Field(gt=0)


class MasterWrite(MasterCreate):
    variety_id: int | None = Field(default=None, gt=0)


class MasterResponse(MasterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProductResponse(MasterResponse):
    variety_id: int


class MasterListResponse(BaseModel):
    items: list[ProductResponse | MasterResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class MaterialInput(BaseModel):
    tea_leaf_id: int = Field(gt=0)
    variety_id: int = Field(gt=0)
    planned_quantity: Quantity


class ManufacturingOrderCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=30)
    product_id: int = Field(gt=0)
    planned_quantity: Quantity
    planned_date: date
    equipment_id: int = Field(gt=0)
    materials: list[MaterialInput] = Field(min_length=1)


class MaterialResponse(MaterialInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tea_leaf_name: str
    variety_name: str

    @field_serializer("planned_quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ProcessDetailResponse(BaseModel):
    id: int
    sequence: int
    process_code: str
    process_name: str
    status: ProcessStatus
    equipment_id: int | None
    equipment_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    result_note: str | None


class OrderInventoryTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inventory_kind: InventoryKind
    transaction_type: InventoryTransactionType
    quantity_delta: Decimal
    balance_after: Decimal
    occurred_at: datetime

    @field_serializer("quantity_delta", "balance_after", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ManufacturingOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_number: str
    product_id: int
    product_name: str
    planned_quantity: Decimal
    planned_date: date
    equipment_id: int
    equipment_name: str
    status: ManufacturingStatus
    started_at: datetime | None
    completed_at: datetime | None
    materials: list[MaterialResponse]
    processes: list[ProcessDetailResponse]
    inventory_transactions: list[OrderInventoryTransactionResponse]

    @field_serializer("planned_quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ManufacturingOrderListResponse(BaseModel):
    items: list[ManufacturingOrderResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
