from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.manufacturing import Equipment, Product, Supplier, TeaLeaf, Variety
from app.schemas.manufacturing import MasterCreate, MasterResponse, ProductCreate, ProductResponse
from app.schemas.phase3 import MasterUpdate
from app.services.manufacturing import create_master, update_master

router = APIRouter(prefix="/masters", tags=["masters"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/tea-leaves", response_model=list[MasterResponse])
def list_tea_leaves(session: DbSession) -> list[TeaLeaf]:
    return list(session.scalars(select(TeaLeaf).order_by(TeaLeaf.code)))


@router.post("/tea-leaves", response_model=MasterResponse, status_code=status.HTTP_201_CREATED)
def create_tea_leaf(payload: MasterCreate, session: DbSession) -> TeaLeaf:
    return create_master(session, TeaLeaf, payload.model_dump())


@router.get("/varieties", response_model=list[MasterResponse])
def list_varieties(session: DbSession) -> list[Variety]:
    return list(session.scalars(select(Variety).order_by(Variety.code)))


@router.post("/varieties", response_model=MasterResponse, status_code=status.HTTP_201_CREATED)
def create_variety(payload: MasterCreate, session: DbSession) -> Variety:
    return create_master(session, Variety, payload.model_dump())


@router.get("/equipment", response_model=list[MasterResponse])
def list_equipment(session: DbSession) -> list[Equipment]:
    return list(session.scalars(select(Equipment).order_by(Equipment.code)))


@router.post("/equipment", response_model=MasterResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(payload: MasterCreate, session: DbSession) -> Equipment:
    return create_master(session, Equipment, payload.model_dump())


@router.get("/equipment/{equipment_id}", response_model=MasterResponse)
def equipment_detail(equipment_id: int, session: DbSession) -> Equipment:
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise NotFoundError("設備が見つかりません。")
    return equipment


@router.put("/equipment/{equipment_id}", response_model=MasterResponse)
def edit_equipment(equipment_id: int, payload: MasterUpdate, session: DbSession) -> Equipment:
    return update_master(session, Equipment, equipment_id, payload.model_dump())


@router.get("/suppliers", response_model=list[MasterResponse])
def list_suppliers(session: DbSession) -> list[Supplier]:
    return list(session.scalars(select(Supplier).order_by(Supplier.code)))


@router.post("/suppliers", response_model=MasterResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: MasterCreate, session: DbSession) -> Supplier:
    return create_master(session, Supplier, payload.model_dump())


@router.get("/products", response_model=list[ProductResponse])
def list_products(session: DbSession) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.code)))


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: DbSession) -> Product:
    return create_master(session, Product, payload.model_dump())
