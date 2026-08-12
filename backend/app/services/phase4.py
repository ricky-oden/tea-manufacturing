from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.manufacturing import (
    InventoryKind,
    InventoryTransaction,
    InventoryTransactionType,
    ManufacturingOrder,
    ManufacturingStatus,
    Product,
    ProductInventoryBalance,
    RawMaterialInventoryBalance,
    RawMaterialReceipt,
    RawMaterialReceiptLine,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
    TeaLeaf,
    Variety,
)
from app.schemas.phase4 import (
    BreakdownItem,
    DashboardResponse,
    InventoryOverview,
    ShipmentResponse,
    ShipmentWrite,
    SummaryResponse,
)
from app.services.manufacturing import _active

TOKYO_TIMEZONE = "Asia/Tokyo"


def validate_period(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise ValidationError("開始日は終了日以前にしてください。")


def _shipment_statement():
    return select(Shipment).options(selectinload(Shipment.lines).selectinload(ShipmentLine.product))


def get_shipment(session: Session, shipment_id: int, *, lock: bool = False) -> Shipment:
    statement = _shipment_statement().where(Shipment.id == shipment_id)
    if lock:
        statement = statement.with_for_update()
    shipment = session.scalar(statement)
    if shipment is None:
        raise NotFoundError("出荷が見つかりません。")
    return shipment


def shipment_response(shipment: Shipment) -> ShipmentResponse:
    return ShipmentResponse.model_validate(
        {
            **shipment.__dict__,
            "lines": [
                {
                    **line.__dict__,
                    "product_code": line.product.code,
                    "product_name": line.product.name,
                }
                for line in shipment.lines
            ],
        }
    )


def _validate_shipment_products(session: Session, payload: ShipmentWrite) -> None:
    for line in payload.lines:
        _active(session, Product, line.product_id, "製品")


def create_shipment(session: Session, payload: ShipmentWrite) -> Shipment:
    _validate_shipment_products(session, payload)
    shipment = Shipment(
        shipment_number=payload.shipment_number,
        shipped_date=payload.shipped_date,
        status=ShipmentStatus.DRAFT,
        lines=[ShipmentLine(**line.model_dump()) for line in payload.lines],
    )
    session.add(shipment)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(
            "同じ出荷番号が既に登録されています。", "DUPLICATE_SHIPMENT_NUMBER"
        ) from exc
    return get_shipment(session, shipment.id)


def update_shipment(session: Session, shipment_id: int, payload: ShipmentWrite) -> Shipment:
    shipment = get_shipment(session, shipment_id, lock=True)
    if shipment.status is not ShipmentStatus.DRAFT:
        raise ConflictError("確定済み出荷は編集できません。", "SHIPMENT_ALREADY_CONFIRMED")
    _validate_shipment_products(session, payload)
    shipment.shipment_number = payload.shipment_number
    shipment.shipped_date = payload.shipped_date
    shipment.lines.clear()
    session.flush()
    shipment.lines = [ShipmentLine(**line.model_dump()) for line in payload.lines]
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(
            "同じ出荷番号が既に登録されています。", "DUPLICATE_SHIPMENT_NUMBER"
        ) from exc
    return get_shipment(session, shipment.id)


def list_shipments(session: Session, page: int, page_size: int) -> tuple[list[Shipment], int]:
    total = session.scalar(select(func.count()).select_from(Shipment)) or 0
    items = session.scalars(
        _shipment_statement()
        .order_by(Shipment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def confirm_shipment(session: Session, shipment_id: int) -> Shipment:
    shipment = get_shipment(session, shipment_id, lock=True)
    if shipment.status is not ShipmentStatus.DRAFT:
        raise ConflictError("下書き出荷だけ確定できます。", "SHIPMENT_ALREADY_CONFIRMED")
    product_ids = sorted(line.product_id for line in shipment.lines)
    balances = session.scalars(
        select(ProductInventoryBalance)
        .where(ProductInventoryBalance.product_id.in_(product_ids))
        .order_by(ProductInventoryBalance.product_id)
        .with_for_update()
    ).all()
    balance_by_product = {balance.product_id: balance for balance in balances}
    for line in shipment.lines:
        balance = balance_by_product.get(line.product_id)
        if balance is None or balance.quantity < line.quantity:
            raise ConflictError("製品在庫が不足しています。", "INSUFFICIENT_PRODUCT_INVENTORY")
    for line in sorted(shipment.lines, key=lambda item: item.product_id):
        balance = balance_by_product[line.product_id]
        balance.quantity -= line.quantity
        session.add(
            InventoryTransaction(
                inventory_kind=InventoryKind.PRODUCT,
                transaction_type=InventoryTransactionType.SHIPMENT,
                product_id=line.product_id,
                quantity_delta=-line.quantity,
                balance_after=balance.quantity,
                reference_type="SHIPMENT_LINE",
                reference_id=line.id,
            )
        )
    shipment.status = ShipmentStatus.CONFIRMED
    shipment.confirmed_at = datetime.now(UTC)
    session.commit()
    return get_shipment(session, shipment.id)


def list_raw_balances(session: Session, page: int, page_size: int):
    total = session.scalar(select(func.count()).select_from(RawMaterialInventoryBalance)) or 0
    rows = session.execute(
        select(RawMaterialInventoryBalance, TeaLeaf, Variety)
        .join(TeaLeaf, TeaLeaf.id == RawMaterialInventoryBalance.tea_leaf_id)
        .join(Variety, Variety.id == RawMaterialInventoryBalance.variety_id)
        .order_by(TeaLeaf.code, Variety.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [
        {
            **balance.__dict__,
            "tea_leaf_code": tea.code,
            "tea_leaf_name": tea.name,
            "variety_code": variety.code,
            "variety_name": variety.name,
        }
        for balance, tea, variety in rows
    ], total


def list_product_balances(session: Session, page: int, page_size: int):
    total = session.scalar(select(func.count()).select_from(ProductInventoryBalance)) or 0
    rows = session.execute(
        select(ProductInventoryBalance, Product)
        .join(Product, Product.id == ProductInventoryBalance.product_id)
        .order_by(Product.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [
        {
            **balance.__dict__,
            "product_code": product.code,
            "product_name": product.name,
        }
        for balance, product in rows
    ], total


def list_inventory_transactions(
    session: Session,
    *,
    page: int,
    page_size: int,
    inventory_kind: InventoryKind | None,
    transaction_type: InventoryTransactionType | None,
    tea_leaf_id: int | None,
    variety_id: int | None,
    product_id: int | None,
    date_from: date | None,
    date_to: date | None,
):
    if date_from and date_to:
        validate_period(date_from, date_to)
    local_date = cast(func.timezone(TOKYO_TIMEZONE, InventoryTransaction.occurred_at), Date)
    conditions = []
    for column, value in [
        (InventoryTransaction.inventory_kind, inventory_kind),
        (InventoryTransaction.transaction_type, transaction_type),
        (InventoryTransaction.tea_leaf_id, tea_leaf_id),
        (InventoryTransaction.variety_id, variety_id),
        (InventoryTransaction.product_id, product_id),
    ]:
        if value is not None:
            conditions.append(column == value)
    if date_from:
        conditions.append(local_date >= date_from)
    if date_to:
        conditions.append(local_date <= date_to)
    where_clause = and_(*conditions) if conditions else True
    total = (
        session.scalar(select(func.count()).select_from(InventoryTransaction).where(where_clause))
        or 0
    )
    rows = session.execute(
        select(InventoryTransaction, TeaLeaf, Variety, Product)
        .outerjoin(TeaLeaf, TeaLeaf.id == InventoryTransaction.tea_leaf_id)
        .outerjoin(Variety, Variety.id == InventoryTransaction.variety_id)
        .outerjoin(Product, Product.id == InventoryTransaction.product_id)
        .where(where_clause)
        .order_by(InventoryTransaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for transaction, tea, variety, product in rows:
        if product:
            target_code, target_name = product.code, product.name
        else:
            target_code = f"{tea.code}/{variety.code}"
            target_name = f"{tea.name} / {variety.name}"
        items.append(
            {**transaction.__dict__, "target_code": target_code, "target_name": target_name}
        )
    return items, total


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(value or 0)


def get_summary(session: Session, date_from: date, date_to: date) -> SummaryResponse:
    validate_period(date_from, date_to)
    receipt_total = session.scalar(
        select(func.coalesce(func.sum(RawMaterialReceiptLine.quantity), 0))
        .join(RawMaterialReceipt)
        .where(RawMaterialReceipt.received_date.between(date_from, date_to))
    )
    completed_local_date = cast(
        func.timezone(TOKYO_TIMEZONE, ManufacturingOrder.completed_at), Date
    )
    manufacturing_total = session.scalar(
        select(func.coalesce(func.sum(ManufacturingOrder.planned_quantity), 0)).where(
            ManufacturingOrder.status == ManufacturingStatus.COMPLETED,
            completed_local_date.between(date_from, date_to),
        )
    )
    shipment_total = session.scalar(
        select(func.coalesce(func.sum(ShipmentLine.quantity), 0))
        .join(Shipment)
        .where(
            Shipment.status == ShipmentStatus.CONFIRMED,
            Shipment.shipped_date.between(date_from, date_to),
        )
    )
    raw_total = session.scalar(
        select(func.coalesce(func.sum(RawMaterialInventoryBalance.quantity), 0))
    )
    product_total = session.scalar(
        select(func.coalesce(func.sum(ProductInventoryBalance.quantity), 0))
    )
    receipt_rows = session.execute(
        select(
            TeaLeaf.code,
            TeaLeaf.name,
            Variety.code,
            Variety.name,
            func.sum(RawMaterialReceiptLine.quantity),
        )
        .join(RawMaterialReceipt, RawMaterialReceipt.id == RawMaterialReceiptLine.receipt_id)
        .join(TeaLeaf, TeaLeaf.id == RawMaterialReceiptLine.tea_leaf_id)
        .join(Variety, Variety.id == RawMaterialReceiptLine.variety_id)
        .where(RawMaterialReceipt.received_date.between(date_from, date_to))
        .group_by(TeaLeaf.id, Variety.id)
        .order_by(TeaLeaf.code, Variety.code)
    ).all()
    manufacturing_rows = session.execute(
        select(Product.code, Product.name, func.sum(ManufacturingOrder.planned_quantity))
        .join(Product, Product.id == ManufacturingOrder.product_id)
        .where(
            ManufacturingOrder.status == ManufacturingStatus.COMPLETED,
            completed_local_date.between(date_from, date_to),
        )
        .group_by(Product.id)
        .order_by(Product.code)
    ).all()
    shipment_rows = session.execute(
        select(Product.code, Product.name, func.sum(ShipmentLine.quantity))
        .join(Shipment, Shipment.id == ShipmentLine.shipment_id)
        .join(Product, Product.id == ShipmentLine.product_id)
        .where(
            Shipment.status == ShipmentStatus.CONFIRMED,
            Shipment.shipped_date.between(date_from, date_to),
        )
        .group_by(Product.id)
        .order_by(Product.code)
    ).all()
    return SummaryResponse(
        date_from=date_from,
        date_to=date_to,
        receipt_quantity=_decimal(receipt_total),
        manufacturing_quantity=_decimal(manufacturing_total),
        shipment_quantity=_decimal(shipment_total),
        current_raw_material_quantity=_decimal(raw_total),
        current_product_quantity=_decimal(product_total),
        receipt_breakdown=[
            BreakdownItem(
                code=f"{tea_code}/{variety_code}",
                name=f"{tea_name} / {variety_name}",
                quantity=_decimal(quantity),
            )
            for tea_code, tea_name, variety_code, variety_name, quantity in receipt_rows
        ],
        manufacturing_breakdown=[
            BreakdownItem(code=code, name=name, quantity=_decimal(quantity))
            for code, name, quantity in manufacturing_rows
        ],
        shipment_breakdown=[
            BreakdownItem(code=code, name=name, quantity=_decimal(quantity))
            for code, name, quantity in shipment_rows
        ],
    )


def get_dashboard(session: Session, date_from: date, date_to: date) -> DashboardResponse:
    summary = get_summary(session, date_from, date_to)
    status_rows = dict(
        session.execute(
            select(ManufacturingOrder.status, func.count()).group_by(ManufacturingOrder.status)
        ).all()
    )
    status_counts = {status: int(status_rows.get(status, 0)) for status in ManufacturingStatus}
    raw_count = session.scalar(select(func.count()).select_from(RawMaterialInventoryBalance)) or 0
    product_count = session.scalar(select(func.count()).select_from(ProductInventoryBalance)) or 0
    return DashboardResponse(
        date_from=date_from,
        date_to=date_to,
        manufacturing_status_counts=status_counts,
        raw_material_inventory=InventoryOverview(
            item_count=raw_count, total_quantity=summary.current_raw_material_quantity
        ),
        product_inventory=InventoryOverview(
            item_count=product_count, total_quantity=summary.current_product_quantity
        ),
        receipt_quantity=summary.receipt_quantity,
        manufacturing_quantity=summary.manufacturing_quantity,
        shipment_quantity=summary.shipment_quantity,
    )
