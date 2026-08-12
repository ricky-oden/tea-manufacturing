from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.manufacturing import ManufacturingStatus
from app.schemas.manufacturing import (
    ManufacturingOrderCreate,
    ManufacturingOrderListResponse,
    ManufacturingOrderResponse,
)
from app.services.manufacturing import (
    change_simple_status,
    complete_order,
    create_order,
    get_order,
    issue_order,
    list_orders,
    order_response,
    start_order,
)

router = APIRouter(prefix="/manufacturing-orders", tags=["manufacturing-orders"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ManufacturingOrderListResponse)
def orders(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    order_status: Annotated[ManufacturingStatus | None, Query(alias="status")] = None,
) -> ManufacturingOrderListResponse:
    items, total = list_orders(session, page, page_size, order_status)
    return ManufacturingOrderListResponse(
        items=[order_response(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size),
    )


@router.post("", response_model=ManufacturingOrderResponse, status_code=status.HTTP_201_CREATED)
def add_order(payload: ManufacturingOrderCreate, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(create_order(session, payload))


@router.get("/{order_id}", response_model=ManufacturingOrderResponse)
def order_detail(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(get_order(session, order_id))


@router.post("/{order_id}/issue", response_model=ManufacturingOrderResponse)
def issue(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(issue_order(session, order_id))


@router.post("/{order_id}/cancel", response_model=ManufacturingOrderResponse)
def cancel(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(
        change_simple_status(
            session,
            order_id,
            (ManufacturingStatus.DRAFT, ManufacturingStatus.ISSUED),
            ManufacturingStatus.CANCELLED,
        )
    )


@router.post("/{order_id}/start", response_model=ManufacturingOrderResponse)
def start(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(start_order(session, order_id))


@router.post("/{order_id}/complete", response_model=ManufacturingOrderResponse)
def complete(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(complete_order(session, order_id))
