from datetime import UTC, datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.manufacturing import (
    Equipment,
    InventoryKind,
    InventoryTransaction,
    InventoryTransactionType,
    ManufacturingOrder,
    ManufacturingProcess,
    ManufacturingStatus,
    ProcessStatus,
    RawMaterialInventoryBalance,
    RawMaterialReceipt,
    RawMaterialReceiptLine,
    Supplier,
    TeaLeaf,
    Variety,
)
from app.schemas.phase3 import ProcessResponse, ProcessUpdate, ReceiptCreate, ReceiptResponse
from app.services.manufacturing import _active

PROCESS_DEFINITIONS = (
    (1, "STEAMING", "蒸熱"),
    (2, "ROLLING", "揉捻"),
    (3, "DRYING", "乾燥"),
)


def create_receipt(session: Session, payload: ReceiptCreate) -> RawMaterialReceipt:
    _active(session, Supplier, payload.supplier_id, "仕入先")
    for line in payload.lines:
        _active(session, TeaLeaf, line.tea_leaf_id, "茶葉")
        _active(session, Variety, line.variety_id, "品種")

    receipt = RawMaterialReceipt(
        receipt_number=payload.receipt_number,
        received_date=payload.received_date,
        supplier_id=payload.supplier_id,
        lines=[RawMaterialReceiptLine(**line.model_dump()) for line in payload.lines],
    )
    session.add(receipt)
    try:
        session.flush()
        keys = sorted({(line.tea_leaf_id, line.variety_id) for line in receipt.lines})
        for tea_leaf_id, variety_id in keys:
            session.execute(
                insert(RawMaterialInventoryBalance)
                .values(
                    tea_leaf_id=tea_leaf_id,
                    variety_id=variety_id,
                    quantity=0,
                )
                .on_conflict_do_nothing(constraint="uq_raw_balance_material")
            )
        balances = session.scalars(
            select(RawMaterialInventoryBalance)
            .where(
                tuple_(
                    RawMaterialInventoryBalance.tea_leaf_id,
                    RawMaterialInventoryBalance.variety_id,
                ).in_(keys)
            )
            .order_by(
                RawMaterialInventoryBalance.tea_leaf_id,
                RawMaterialInventoryBalance.variety_id,
            )
            .with_for_update()
        ).all()
        balance_by_key = {(item.tea_leaf_id, item.variety_id): item for item in balances}
        for line in receipt.lines:
            balance = balance_by_key[(line.tea_leaf_id, line.variety_id)]
            balance.quantity += line.quantity
            session.add(
                InventoryTransaction(
                    inventory_kind=InventoryKind.RAW_MATERIAL,
                    transaction_type=InventoryTransactionType.RECEIPT,
                    tea_leaf_id=line.tea_leaf_id,
                    variety_id=line.variety_id,
                    quantity_delta=line.quantity,
                    balance_after=balance.quantity,
                    reference_type="RAW_MATERIAL_RECEIPT_LINE",
                    reference_id=line.id,
                )
            )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(
            "同じ入荷番号が既に登録されています。", "DUPLICATE_RECEIPT_NUMBER"
        ) from exc
    return get_receipt(session, receipt.id)


def get_receipt(session: Session, receipt_id: int) -> RawMaterialReceipt:
    receipt = session.scalar(
        select(RawMaterialReceipt)
        .where(RawMaterialReceipt.id == receipt_id)
        .options(
            selectinload(RawMaterialReceipt.supplier),
            selectinload(RawMaterialReceipt.lines).selectinload(RawMaterialReceiptLine.tea_leaf),
            selectinload(RawMaterialReceipt.lines).selectinload(RawMaterialReceiptLine.variety),
        )
    )
    if receipt is None:
        raise NotFoundError("原料入荷が見つかりません。")
    return receipt


def receipt_response(receipt: RawMaterialReceipt) -> ReceiptResponse:
    return ReceiptResponse.model_validate(
        {
            **receipt.__dict__,
            "supplier_name": receipt.supplier.name,
            "lines": [
                {
                    **line.__dict__,
                    "tea_leaf_name": line.tea_leaf.name,
                    "variety_name": line.variety.name,
                }
                for line in receipt.lines
            ],
        }
    )


def list_receipts(
    session: Session, page: int, page_size: int
) -> tuple[list[RawMaterialReceipt], int]:
    total = session.scalar(select(func.count()).select_from(RawMaterialReceipt)) or 0
    items = session.scalars(
        select(RawMaterialReceipt)
        .options(
            selectinload(RawMaterialReceipt.supplier),
            selectinload(RawMaterialReceipt.lines).selectinload(RawMaterialReceiptLine.tea_leaf),
            selectinload(RawMaterialReceipt.lines).selectinload(RawMaterialReceiptLine.variety),
        )
        .order_by(RawMaterialReceipt.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def process_response(process: ManufacturingProcess) -> ProcessResponse:
    return ProcessResponse.model_validate(
        {
            **process.__dict__,
            "equipment_name": process.equipment.name if process.equipment else None,
        }
    )


def list_processes(session: Session, order_id: int) -> list[ManufacturingProcess]:
    if session.get(ManufacturingOrder, order_id) is None:
        raise NotFoundError("製造指示が見つかりません。")
    return list(
        session.scalars(
            select(ManufacturingProcess)
            .where(ManufacturingProcess.manufacturing_order_id == order_id)
            .options(selectinload(ManufacturingProcess.equipment))
            .order_by(ManufacturingProcess.sequence)
        )
    )


def update_process(
    session: Session,
    order_id: int,
    process_id: int,
    payload: ProcessUpdate,
) -> ManufacturingProcess:
    order = session.scalar(
        select(ManufacturingOrder).where(ManufacturingOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise NotFoundError("製造指示が見つかりません。")
    if order.status is not ManufacturingStatus.IN_PROGRESS:
        raise ConflictError("製造中の指示だけ工程操作できます。", "INVALID_PROCESS_STATE")
    process = session.scalar(
        select(ManufacturingProcess)
        .where(
            ManufacturingProcess.id == process_id,
            ManufacturingProcess.manufacturing_order_id == order_id,
        )
        .options(selectinload(ManufacturingProcess.equipment))
        .with_for_update()
    )
    if process is None:
        raise NotFoundError("製造工程が見つかりません。")
    prior_incomplete = session.scalar(
        select(func.count())
        .select_from(ManufacturingProcess)
        .where(
            ManufacturingProcess.manufacturing_order_id == order_id,
            ManufacturingProcess.sequence < process.sequence,
            ManufacturingProcess.status != ProcessStatus.COMPLETED,
        )
    )
    if prior_incomplete:
        raise ConflictError("前工程が完了していません。", "PROCESS_SEQUENCE_VIOLATION")
    if payload.equipment_id is not None:
        _active(session, Equipment, payload.equipment_id, "設備")
        process.equipment_id = payload.equipment_id
    if payload.result_note is not None:
        process.result_note = payload.result_note
    if payload.action == "start":
        if process.status is not ProcessStatus.PENDING:
            raise ConflictError("未開始の工程だけ開始できます。", "INVALID_PROCESS_STATE")
        process.status = ProcessStatus.IN_PROGRESS
        process.started_at = datetime.now(UTC)
    else:
        if process.status is not ProcessStatus.IN_PROGRESS:
            raise ConflictError("実行中の工程だけ完了できます。", "INVALID_PROCESS_STATE")
        process.status = ProcessStatus.COMPLETED
        process.completed_at = datetime.now(UTC)
    session.commit()
    return session.scalar(
        select(ManufacturingProcess)
        .where(ManufacturingProcess.id == process.id)
        .options(selectinload(ManufacturingProcess.equipment))
    )
