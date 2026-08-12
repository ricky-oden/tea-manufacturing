from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.pagination import PAGE_SIZE_MAX, page_response
from app.db.session import get_db
from app.models.manufacturing import Equipment, Product, Supplier, TeaLeaf, Variety
from app.schemas.manufacturing import (
    MasterListResponse,
    MasterResponse,
    MasterWrite,
    ProductResponse,
)
from app.services.manufacturing import create_master, get_master, list_masters, update_master

router = APIRouter(prefix="/masters", tags=["masters"])
DbSession = Annotated[Session, Depends(get_db)]
MasterResource = Literal["tea-leaves", "varieties", "suppliers", "equipment", "products"]
MASTER_MODELS = {
    "tea-leaves": TeaLeaf,
    "varieties": Variety,
    "suppliers": Supplier,
    "equipment": Equipment,
    "products": Product,
}


@router.get("/{resource}", response_model=MasterListResponse)
def masters(
    resource: MasterResource,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=PAGE_SIZE_MAX),
):
    items, total = list_masters(session, MASTER_MODELS[resource], page, page_size)
    return page_response(items, page, page_size, total)


@router.post(
    "/{resource}",
    response_model=ProductResponse | MasterResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_master(resource: MasterResource, payload: MasterWrite, session: DbSession):
    return create_master(session, MASTER_MODELS[resource], payload.model_dump())


@router.get("/{resource}/{master_id}", response_model=ProductResponse | MasterResponse)
def master_detail(resource: MasterResource, master_id: int, session: DbSession):
    return get_master(session, MASTER_MODELS[resource], master_id)


@router.put("/{resource}/{master_id}", response_model=ProductResponse | MasterResponse)
def edit_master(resource: MasterResource, master_id: int, payload: MasterWrite, session: DbSession):
    return update_master(session, MASTER_MODELS[resource], master_id, payload.model_dump())
