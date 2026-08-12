from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.pagination import PAGE_SIZE_MAX, page_response
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
    update_order,
)

router = APIRouter(prefix="/manufacturing-orders", tags=["manufacturing-orders"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ManufacturingOrderListResponse)
def orders(
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=PAGE_SIZE_MAX),
    status: ManufacturingStatus | None = None,
    product_id: int | None = None,
    planned_date_from: date | None = None,
    planned_date_to: date | None = None,
) -> ManufacturingOrderListResponse:
    items, total = list_orders(
        session, page, page_size, status, product_id, planned_date_from, planned_date_to
    )
    return ManufacturingOrderListResponse.model_validate(
        page_response([order_response(session, item) for item in items], page, page_size, total)
    )


@router.post("", response_model=ManufacturingOrderResponse, status_code=status.HTTP_201_CREATED)
def add_order(payload: ManufacturingOrderCreate, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(session, create_order(session, payload))


@router.get("/{order_id}", response_model=ManufacturingOrderResponse)
def order_detail(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(session, get_order(session, order_id))


@router.put("/{order_id}", response_model=ManufacturingOrderResponse)
def edit_order(
    order_id: int, payload: ManufacturingOrderCreate, session: DbSession
) -> ManufacturingOrderResponse:
    return order_response(session, update_order(session, order_id, payload))


@router.post("/{order_id}/issue", response_model=ManufacturingOrderResponse)
def issue(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(session, issue_order(session, order_id))


@router.post("/{order_id}/cancel", response_model=ManufacturingOrderResponse)
def cancel(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(
        session,
        change_simple_status(
            session,
            order_id,
            (ManufacturingStatus.DRAFT, ManufacturingStatus.ISSUED),
            ManufacturingStatus.CANCELLED,
        ),
    )


@router.post("/{order_id}/start", response_model=ManufacturingOrderResponse)
def start(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(session, start_order(session, order_id))


@router.post("/{order_id}/complete", response_model=ManufacturingOrderResponse)
def complete(order_id: int, session: DbSession) -> ManufacturingOrderResponse:
    return order_response(session, complete_order(session, order_id))
