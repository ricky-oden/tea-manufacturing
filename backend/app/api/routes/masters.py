from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.manufacturing import Equipment, Product, TeaLeaf, Variety
from app.schemas.manufacturing import MasterCreate, MasterResponse, ProductCreate, ProductResponse
from app.services.manufacturing import create_master

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


@router.get("/products", response_model=list[ProductResponse])
def list_products(session: DbSession) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.code)))


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: DbSession) -> Product:
    return create_master(session, Product, payload.model_dump())
