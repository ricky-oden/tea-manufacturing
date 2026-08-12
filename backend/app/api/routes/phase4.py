from datetime import date
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.manufacturing import InventoryKind, InventoryTransactionType
from app.schemas.phase4 import (
    DashboardResponse,
    InventoryTransactionResponse,
    PageResponse,
    ProductBalanceResponse,
    RawBalanceResponse,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentWrite,
    SummaryResponse,
)
from app.services.phase4 import (
    confirm_shipment,
    create_shipment,
    get_dashboard,
    get_shipment,
    get_summary,
    list_inventory_transactions,
    list_product_balances,
    list_raw_balances,
    list_shipments,
    shipment_response,
    update_shipment,
)

router = APIRouter(tags=["phase4"])
DbSession = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def page_response(items: list, page: int, page_size: int, total: int) -> dict:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": ceil(total / page_size),
    }


@router.get("/inventories/raw-materials", response_model=PageResponse)
def raw_balances(session: DbSession, page: Page = 1, page_size: PageSize = 20) -> dict:
    items, total = list_raw_balances(session, page, page_size)
    return page_response(
        [RawBalanceResponse.model_validate(item) for item in items], page, page_size, total
    )


@router.get("/inventories/products", response_model=PageResponse)
def product_balances(session: DbSession, page: Page = 1, page_size: PageSize = 20) -> dict:
    items, total = list_product_balances(session, page, page_size)
    return page_response(
        [ProductBalanceResponse.model_validate(item) for item in items], page, page_size, total
    )


@router.get("/inventory-transactions", response_model=PageResponse)
def inventory_transactions(
    session: DbSession,
    page: Page = 1,
    page_size: PageSize = 20,
    inventory_kind: InventoryKind | None = None,
    transaction_type: InventoryTransactionType | None = None,
    tea_leaf_id: int | None = None,
    variety_id: int | None = None,
    product_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    items, total = list_inventory_transactions(
        session,
        page=page,
        page_size=page_size,
        inventory_kind=inventory_kind,
        transaction_type=transaction_type,
        tea_leaf_id=tea_leaf_id,
        variety_id=variety_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
    )
    return page_response(
        [InventoryTransactionResponse.model_validate(item) for item in items],
        page,
        page_size,
        total,
    )


@router.get("/shipments", response_model=ShipmentListResponse)
def shipments(session: DbSession, page: Page = 1, page_size: PageSize = 20) -> dict:
    items, total = list_shipments(session, page, page_size)
    return page_response([shipment_response(item) for item in items], page, page_size, total)


@router.post("/shipments", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def add_shipment(payload: ShipmentWrite, session: DbSession) -> ShipmentResponse:
    return shipment_response(create_shipment(session, payload))


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def shipment_detail(shipment_id: int, session: DbSession) -> ShipmentResponse:
    return shipment_response(get_shipment(session, shipment_id))


@router.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
def edit_shipment(shipment_id: int, payload: ShipmentWrite, session: DbSession) -> ShipmentResponse:
    return shipment_response(update_shipment(session, shipment_id, payload))


@router.post("/shipments/{shipment_id}/confirm", response_model=ShipmentResponse)
def confirm(shipment_id: int, session: DbSession) -> ShipmentResponse:
    return shipment_response(confirm_shipment(session, shipment_id))


@router.get("/reports/summary", response_model=SummaryResponse)
def summary(date_from: date, date_to: date, session: DbSession) -> SummaryResponse:
    return get_summary(session, date_from, date_to)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(date_from: date, date_to: date, session: DbSession) -> DashboardResponse:
    return get_dashboard(session, date_from, date_to)
