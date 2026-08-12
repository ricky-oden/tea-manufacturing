from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.pagination import PAGE_SIZE_MAX, page_response
from app.db.session import get_db
from app.schemas.phase3 import (
    ProcessResponse,
    ProcessUpdate,
    ReceiptCreate,
    ReceiptListResponse,
    ReceiptResponse,
)
from app.services.phase3 import (
    create_receipt,
    get_receipt,
    list_processes,
    list_receipts,
    process_response,
    receipt_response,
    update_process,
)

router = APIRouter(tags=["phase3"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/raw-material-receipts", response_model=ReceiptListResponse)
def receipts(
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=PAGE_SIZE_MAX),
) -> ReceiptListResponse:
    items, total = list_receipts(session, page, page_size)
    return ReceiptListResponse.model_validate(
        page_response([receipt_response(item) for item in items], page, page_size, total)
    )


@router.post(
    "/raw-material-receipts", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED
)
def add_receipt(payload: ReceiptCreate, session: DbSession) -> ReceiptResponse:
    return receipt_response(create_receipt(session, payload))


@router.get("/raw-material-receipts/{receipt_id}", response_model=ReceiptResponse)
def receipt_detail(receipt_id: int, session: DbSession) -> ReceiptResponse:
    return receipt_response(get_receipt(session, receipt_id))


@router.get("/manufacturing-orders/{order_id}/processes", response_model=list[ProcessResponse])
def processes(order_id: int, session: DbSession) -> list[ProcessResponse]:
    return [process_response(item) for item in list_processes(session, order_id)]


@router.put(
    "/manufacturing-orders/{order_id}/processes/{process_id}",
    response_model=ProcessResponse,
)
def change_process(
    order_id: int,
    process_id: int,
    payload: ProcessUpdate,
    session: DbSession,
) -> ProcessResponse:
    return process_response(update_process(session, order_id, process_id, payload))
