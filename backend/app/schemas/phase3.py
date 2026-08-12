from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.manufacturing import ProcessStatus
from app.schemas.manufacturing import Quantity


class MasterUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    is_active: bool


class ReceiptLineInput(BaseModel):
    tea_leaf_id: int = Field(gt=0)
    variety_id: int = Field(gt=0)
    quantity: Quantity


class ReceiptCreate(BaseModel):
    receipt_number: str = Field(min_length=1, max_length=30)
    received_date: date
    supplier_id: int = Field(gt=0)
    lines: list[ReceiptLineInput] = Field(min_length=1)


class ReceiptLineResponse(ReceiptLineInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tea_leaf_name: str
    variety_name: str

    @field_serializer("quantity", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    received_date: date
    supplier_id: int
    supplier_name: str
    created_at: datetime
    lines: list[ReceiptLineResponse]


class ReceiptListResponse(BaseModel):
    items: list[ReceiptResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ProcessUpdate(BaseModel):
    action: Literal["start", "complete"]
    equipment_id: int | None = Field(default=None, gt=0)
    result_note: str | None = Field(default=None, max_length=500)


class ProcessResponse(BaseModel):
    id: int
    manufacturing_order_id: int
    sequence: int
    process_code: str
    process_name: str
    status: ProcessStatus
    equipment_id: int | None
    equipment_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    result_note: str | None
