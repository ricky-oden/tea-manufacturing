from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessValidationError, ConflictError, NotFoundError, ValidationError
from app.models.manufacturing import (
    Equipment,
    InventoryKind,
    InventoryTransaction,
    InventoryTransactionType,
    ManufacturingMaterial,
    ManufacturingOrder,
    ManufacturingProcess,
    ManufacturingStatus,
    ProcessStatus,
    Product,
    ProductInventoryBalance,
    RawMaterialInventoryBalance,
    TeaLeaf,
    Variety,
)
from app.schemas.manufacturing import ManufacturingOrderCreate, ManufacturingOrderResponse


def _active(session: Session, model: type, identifier: int, label: str):
    instance = session.get(model, identifier)
    if instance is None:
        raise NotFoundError(f"{label}が見つかりません。")
    if not instance.is_active:
        raise BusinessValidationError(f"無効な{label}は使用できません。")
    return instance


def create_master(session: Session, model: type, payload: dict):
    if model is Product:
        if payload.get("variety_id") is None:
            raise BusinessValidationError("製品には品種が必要です。")
        _active(session, Variety, payload["variety_id"], "品種")
    else:
        payload.pop("variety_id", None)
    instance = model(**payload)
    session.add(instance)
    try:
        session.flush()
        if model is Product:
            session.add(ProductInventoryBalance(product_id=instance.id, quantity=Decimal("0.000")))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("同じコードが既に登録されています。", "DUPLICATE_CODE") from exc
    session.refresh(instance)
    return instance


def update_master(session: Session, model: type, identifier: int, payload: dict):
    instance = session.get(model, identifier)
    if instance is None:
        raise NotFoundError("マスタが見つかりません。")
    if model is Product:
        if payload.get("variety_id") is None:
            raise BusinessValidationError("製品には品種が必要です。")
        if payload["variety_id"] != instance.variety_id:
            _active(session, Variety, payload["variety_id"], "品種")
    else:
        payload.pop("variety_id", None)
    for field, value in payload.items():
        setattr(instance, field, value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("同じコードが既に登録されています。", "DUPLICATE_CODE") from exc
    session.refresh(instance)
    return instance


def get_master(session: Session, model: type, identifier: int):
    instance = session.get(model, identifier)
    if instance is None:
        raise NotFoundError("マスタが見つかりません。")
    return instance


def list_masters(session: Session, model: type, page: int, page_size: int):
    total = session.scalar(select(func.count()).select_from(model)) or 0
    items = session.scalars(
        select(model).order_by(model.code).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(items), total


def validate_order_references(session: Session, payload: ManufacturingOrderCreate) -> None:
    _active(session, Product, payload.product_id, "製品")
    _active(session, Equipment, payload.equipment_id, "設備")
    keys: set[tuple[int, int]] = set()
    for material in payload.materials:
        _active(session, TeaLeaf, material.tea_leaf_id, "茶葉")
        _active(session, Variety, material.variety_id, "品種")
        key = (material.tea_leaf_id, material.variety_id)
        if key in keys:
            raise BusinessValidationError("同じ茶葉・品種を重複指定できません。")
        keys.add(key)


def create_order(session: Session, payload: ManufacturingOrderCreate) -> ManufacturingOrder:
    validate_order_references(session, payload)
    order = ManufacturingOrder(
        order_number=payload.order_number,
        product_id=payload.product_id,
        planned_quantity=payload.planned_quantity,
        planned_date=payload.planned_date,
        equipment_id=payload.equipment_id,
        status=ManufacturingStatus.DRAFT,
        materials=[ManufacturingMaterial(**item.model_dump()) for item in payload.materials],
    )
    session.add(order)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("製造指示番号が重複しています。", "DUPLICATE_ORDER_NUMBER") from exc
    return get_order(session, order.id)


def get_order(session: Session, order_id: int, *, lock: bool = False) -> ManufacturingOrder:
    statement = (
        select(ManufacturingOrder)
        .where(ManufacturingOrder.id == order_id)
        .options(
            selectinload(ManufacturingOrder.product),
            selectinload(ManufacturingOrder.equipment),
            selectinload(ManufacturingOrder.materials).selectinload(ManufacturingMaterial.tea_leaf),
            selectinload(ManufacturingOrder.materials).selectinload(ManufacturingMaterial.variety),
            selectinload(ManufacturingOrder.processes).selectinload(ManufacturingProcess.equipment),
        )
    )
    if lock:
        statement = statement.with_for_update()
    order = session.scalar(statement)
    if order is None:
        raise NotFoundError("製造指示が見つかりません。")
    return order


def order_response(session: Session, order: ManufacturingOrder) -> ManufacturingOrderResponse:
    transactions = session.scalars(
        select(InventoryTransaction)
        .where(
            InventoryTransaction.reference_type == "MANUFACTURING_ORDER",
            InventoryTransaction.reference_id == order.id,
        )
        .order_by(InventoryTransaction.id)
    ).all()
    return ManufacturingOrderResponse.model_validate(
        {
            **order.__dict__,
            "product_name": order.product.name,
            "equipment_name": order.equipment.name,
            "materials": [
                {
                    **material.__dict__,
                    "tea_leaf_name": material.tea_leaf.name,
                    "variety_name": material.variety.name,
                }
                for material in order.materials
            ],
            "processes": [
                {
                    **process.__dict__,
                    "equipment_name": process.equipment.name if process.equipment else None,
                }
                for process in order.processes
            ],
            "inventory_transactions": transactions,
        }
    )


def update_order(
    session: Session, order_id: int, payload: ManufacturingOrderCreate
) -> ManufacturingOrder:
    order = get_order(session, order_id, lock=True)
    if order.status is not ManufacturingStatus.DRAFT:
        raise ConflictError("下書きの製造指示だけ編集できます。", "INVALID_STATUS_TRANSITION")
    validate_order_references(session, payload)
    order.order_number = payload.order_number
    order.product_id = payload.product_id
    order.planned_quantity = payload.planned_quantity
    order.planned_date = payload.planned_date
    order.equipment_id = payload.equipment_id
    order.materials.clear()
    session.flush()
    order.materials = [ManufacturingMaterial(**item.model_dump()) for item in payload.materials]
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("製造指示番号が重複しています。", "DUPLICATE_ORDER_NUMBER") from exc
    return get_order(session, order.id)


def change_simple_status(
    session: Session,
    order_id: int,
    expected: tuple[ManufacturingStatus, ...],
    target: ManufacturingStatus,
) -> ManufacturingOrder:
    order = get_order(session, order_id, lock=True)
    if order.status not in expected:
        raise ConflictError("現在の製造状態では実行できません。", "INVALID_STATUS_TRANSITION")
    order.status = target
    session.commit()
    return get_order(session, order_id)


def issue_order(session: Session, order_id: int) -> ManufacturingOrder:
    order = get_order(session, order_id, lock=True)
    if order.status is not ManufacturingStatus.DRAFT:
        raise ConflictError("下書きの製造指示だけ指示確定できます。", "INVALID_STATUS_TRANSITION")
    _active(session, Product, order.product_id, "製品")
    _active(session, Equipment, order.equipment_id, "設備")
    for material in order.materials:
        _active(session, TeaLeaf, material.tea_leaf_id, "茶葉")
        _active(session, Variety, material.variety_id, "品種")
    if not order.processes:
        from app.services.phase3 import PROCESS_DEFINITIONS

        order.processes = [
            ManufacturingProcess(
                sequence=sequence,
                process_code=process_code,
                process_name=process_name,
                status=ProcessStatus.PENDING,
            )
            for sequence, process_code, process_name in PROCESS_DEFINITIONS
        ]
    order.status = ManufacturingStatus.ISSUED
    session.commit()
    return get_order(session, order_id)


def start_order(session: Session, order_id: int) -> ManufacturingOrder:
    order = get_order(session, order_id, lock=True)
    if order.status is not ManufacturingStatus.ISSUED:
        raise ConflictError("指示済みの製造指示だけ開始できます。", "INVALID_STATUS_TRANSITION")
    balances: list[tuple[ManufacturingMaterial, RawMaterialInventoryBalance]] = []
    for material in sorted(order.materials, key=lambda item: (item.tea_leaf_id, item.variety_id)):
        _active(session, TeaLeaf, material.tea_leaf_id, "茶葉")
        _active(session, Variety, material.variety_id, "品種")
        balance = session.scalar(
            select(RawMaterialInventoryBalance)
            .where(
                RawMaterialInventoryBalance.tea_leaf_id == material.tea_leaf_id,
                RawMaterialInventoryBalance.variety_id == material.variety_id,
            )
            .with_for_update()
        )
        if balance is None or balance.quantity < material.planned_quantity:
            raise ConflictError("原料在庫が不足しています。", "INSUFFICIENT_RAW_MATERIAL")
        balances.append((material, balance))
    for material, balance in balances:
        balance.quantity -= material.planned_quantity
        session.add(
            InventoryTransaction(
                inventory_kind=InventoryKind.RAW_MATERIAL,
                transaction_type=InventoryTransactionType.MANUFACTURING_CONSUMPTION,
                tea_leaf_id=material.tea_leaf_id,
                variety_id=material.variety_id,
                quantity_delta=-material.planned_quantity,
                balance_after=balance.quantity,
                reference_type="MANUFACTURING_ORDER",
                reference_id=order.id,
            )
        )
    order.status = ManufacturingStatus.IN_PROGRESS
    order.started_at = datetime.now(UTC)
    session.commit()
    return get_order(session, order_id)


def complete_order(session: Session, order_id: int) -> ManufacturingOrder:
    order = get_order(session, order_id, lock=True)
    if order.status is not ManufacturingStatus.IN_PROGRESS:
        raise ConflictError("製造中の製造指示だけ完了できます。", "INVALID_STATUS_TRANSITION")
    if order.planned_quantity <= 0:
        raise BusinessValidationError("予定数量は正数である必要があります。")
    if order.processes and any(
        process.status is not ProcessStatus.COMPLETED for process in order.processes
    ):
        raise ConflictError("必須工程が完了していません。", "PROCESS_NOT_COMPLETED")
    product = session.get(Product, order.product_id)
    if product is None:
        raise NotFoundError("製品が見つかりません。")
    balance = session.scalar(
        select(ProductInventoryBalance)
        .where(ProductInventoryBalance.product_id == order.product_id)
        .with_for_update()
    )
    if balance is None:
        balance = ProductInventoryBalance(product_id=order.product_id, quantity=Decimal("0.000"))
        session.add(balance)
        session.flush()
    balance.quantity += order.planned_quantity
    session.add(
        InventoryTransaction(
            inventory_kind=InventoryKind.PRODUCT,
            transaction_type=InventoryTransactionType.MANUFACTURING_OUTPUT,
            product_id=order.product_id,
            quantity_delta=order.planned_quantity,
            balance_after=balance.quantity,
            reference_type="MANUFACTURING_ORDER",
            reference_id=order.id,
        )
    )
    order.status = ManufacturingStatus.COMPLETED
    order.completed_at = datetime.now(UTC)
    session.commit()
    return get_order(session, order_id)


def list_orders(
    session: Session,
    page: int,
    page_size: int,
    status: ManufacturingStatus | None,
    product_id: int | None = None,
    planned_date_from: date | None = None,
    planned_date_to: date | None = None,
) -> tuple[list[ManufacturingOrder], int]:
    conditions = []
    if status:
        conditions.append(ManufacturingOrder.status == status)
    if product_id:
        conditions.append(ManufacturingOrder.product_id == product_id)
    if planned_date_from:
        conditions.append(ManufacturingOrder.planned_date >= planned_date_from)
    if planned_date_to:
        conditions.append(ManufacturingOrder.planned_date <= planned_date_to)
    if planned_date_from and planned_date_to and planned_date_from > planned_date_to:
        raise ValidationError("開始日は終了日以前にしてください。")
    total = (
        session.scalar(select(func.count()).select_from(ManufacturingOrder).where(*conditions)) or 0
    )
    items = session.scalars(
        select(ManufacturingOrder)
        .where(*conditions)
        .options(
            selectinload(ManufacturingOrder.product),
            selectinload(ManufacturingOrder.equipment),
            selectinload(ManufacturingOrder.materials).selectinload(ManufacturingMaterial.tea_leaf),
            selectinload(ManufacturingOrder.materials).selectinload(ManufacturingMaterial.variety),
            selectinload(ManufacturingOrder.processes).selectinload(ManufacturingProcess.equipment),
        )
        .order_by(ManufacturingOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total
