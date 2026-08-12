from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.manufacturing import (
    InventoryTransaction,
    InventoryTransactionType,
    ManufacturingProcess,
    ProductInventoryBalance,
    RawMaterialInventoryBalance,
    RawMaterialReceipt,
    RawMaterialReceiptLine,
    Supplier,
)


def create_master_data(client: TestClient) -> dict[str, int]:
    tea = client.post("/api/v1/masters/tea-leaves", json={"code": "TL-01", "name": "煎茶"}).json()
    tea2 = client.post("/api/v1/masters/tea-leaves", json={"code": "TL-02", "name": "玉露"}).json()
    variety = client.post(
        "/api/v1/masters/varieties", json={"code": "V-01", "name": "やぶきた"}
    ).json()
    equipment = client.post(
        "/api/v1/masters/equipment", json={"code": "EQ-01", "name": "蒸機"}
    ).json()
    supplier = client.post(
        "/api/v1/masters/suppliers", json={"code": "S-01", "name": "茶園A"}
    ).json()
    product = client.post(
        "/api/v1/masters/products",
        json={"code": "P-01", "name": "煎茶製品", "variety_id": variety["id"]},
    ).json()
    return {
        "tea": tea["id"],
        "tea2": tea2["id"],
        "variety": variety["id"],
        "equipment": equipment["id"],
        "supplier": supplier["id"],
        "product": product["id"],
    }


def receipt_payload(ids: dict[str, int], number: str = "RC-0001") -> dict:
    return {
        "receipt_number": number,
        "received_date": "2026-08-12",
        "supplier_id": ids["supplier"],
        "lines": [
            {
                "tea_leaf_id": ids["tea"],
                "variety_id": ids["variety"],
                "quantity": "1.250",
            },
            {
                "tea_leaf_id": ids["tea2"],
                "variety_id": ids["variety"],
                "quantity": "2.500",
            },
        ],
    }


def order_payload(ids: dict[str, int]) -> dict:
    return {
        "order_number": "MO-P3-001",
        "product_id": ids["product"],
        "planned_quantity": "1.000",
        "planned_date": "2026-08-12",
        "equipment_id": ids["equipment"],
        "materials": [
            {
                "tea_leaf_id": ids["tea"],
                "variety_id": ids["variety"],
                "planned_quantity": "1.000",
            }
        ],
    }


def test_multiple_line_receipt_updates_each_balance_and_history(
    client: TestClient, db_session: Session
) -> None:
    ids = create_master_data(client)
    response = client.post("/api/v1/raw-material-receipts", json=receipt_payload(ids))
    assert response.status_code == 201
    assert len(response.json()["lines"]) == 2
    balances = list(
        db_session.scalars(
            select(RawMaterialInventoryBalance).order_by(RawMaterialInventoryBalance.tea_leaf_id)
        )
    )
    assert [item.quantity for item in balances] == [Decimal("1.250"), Decimal("2.500")]
    histories = list(db_session.scalars(select(InventoryTransaction)))
    assert len(histories) == 2
    assert {item.transaction_type for item in histories} == {InventoryTransactionType.RECEIPT}
    listing = client.get("/api/v1/raw-material-receipts?page=1&page_size=20").json()
    assert (listing["total"], listing["total_pages"], len(listing["items"])) == (1, 1, 1)
    detail = client.get(f"/api/v1/raw-material-receipts/{response.json()['id']}")
    assert detail.status_code == 200


def test_receipt_rejects_duplicate_number_inactive_master_and_invalid_quantity(
    client: TestClient, db_session: Session
) -> None:
    ids = create_master_data(client)
    assert (
        client.post("/api/v1/raw-material-receipts", json=receipt_payload(ids)).status_code == 201
    )
    duplicate = client.post("/api/v1/raw-material-receipts", json=receipt_payload(ids))
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_RECEIPT_NUMBER"

    supplier = client.get("/api/v1/masters/suppliers").json()[0]
    stored_supplier = db_session.get(Supplier, supplier["id"])
    stored_supplier.is_active = False
    db_session.commit()
    inactive_payload = receipt_payload(ids, "RC-0002")
    inactive = client.post("/api/v1/raw-material-receipts", json=inactive_payload)
    assert inactive.status_code == 400
    assert inactive.json()["code"] == "BUSINESS_VALIDATION_ERROR"

    invalid_payload = receipt_payload(ids, "RC-0003")
    invalid_payload["lines"][0]["quantity"] = "0"
    invalid = client.post("/api/v1/raw-material-receipts", json=invalid_payload)
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_receipt_forced_exception_rolls_back_everything(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = create_master_data(client)

    def flush_then_fail(session: Session) -> None:
        session.flush()
        raise RuntimeError("phase3-sensitive-error")

    monkeypatch.setattr(Session, "commit", flush_then_fail)
    response = client.post("/api/v1/raw-material-receipts", json=receipt_payload(ids))
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert "phase3-sensitive-error" not in response.text
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(RawMaterialReceipt)) == 0
    assert db_session.scalar(select(func.count()).select_from(RawMaterialReceiptLine)) == 0
    assert db_session.scalar(select(func.count()).select_from(RawMaterialInventoryBalance)) == 0
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 0


def test_concurrent_receipts_lock_new_balance_and_sum_once(
    client: TestClient, db_session: Session
) -> None:
    ids = create_master_data(client)
    barrier = Barrier(3, timeout=5)

    def register(number: str, quantity: str) -> int:
        body = receipt_payload(ids, number)
        body["lines"] = [body["lines"][0]]
        body["lines"][0]["quantity"] = quantity
        with TestClient(create_app(), raise_server_exceptions=False) as concurrent_client:
            barrier.wait()
            return concurrent_client.post("/api/v1/raw-material-receipts", json=body).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(register, "RC-C01", "1.000"),
            executor.submit(register, "RC-C02", "2.000"),
        ]
        barrier.wait()
        statuses = [future.result(timeout=10) for future in futures]
    assert statuses == [201, 201]
    db_session.expire_all()
    assert db_session.scalar(select(RawMaterialInventoryBalance.quantity)) == Decimal("3.000")
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 2
    assert db_session.scalar(select(func.count()).select_from(RawMaterialReceipt)) == 2


def test_receipt_quantity_database_constraint(client: TestClient, db_session: Session) -> None:
    ids = create_master_data(client)
    receipt = RawMaterialReceipt(
        receipt_number="RC-DB-01",
        received_date=date(2026, 8, 12),
        supplier_id=ids["supplier"],
        lines=[
            RawMaterialReceiptLine(
                tea_leaf_id=ids["tea"],
                variety_id=ids["variety"],
                quantity=Decimal("0.000"),
            )
        ],
    )
    db_session.add(receipt)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_fixed_processes_order_and_completion_gate(client: TestClient, db_session: Session) -> None:
    ids = create_master_data(client)
    receipt = receipt_payload(ids)
    receipt["lines"] = [receipt["lines"][0]]
    client.post("/api/v1/raw-material-receipts", json=receipt)
    order_id = client.post("/api/v1/manufacturing-orders", json=order_payload(ids)).json()["id"]
    assert client.post(f"/api/v1/manufacturing-orders/{order_id}/issue").status_code == 200
    processes = client.get(f"/api/v1/manufacturing-orders/{order_id}/processes").json()
    assert [(item["sequence"], item["process_code"]) for item in processes] == [
        (1, "STEAMING"),
        (2, "ROLLING"),
        (3, "DRYING"),
    ]
    assert client.post(f"/api/v1/manufacturing-orders/{order_id}/issue").status_code == 409
    assert db_session.scalar(select(func.count()).select_from(ManufacturingProcess)) == 3
    first_path = f"/api/v1/manufacturing-orders/{order_id}/processes/{processes[0]['id']}"
    assert client.put(first_path, json={"action": "start"}).status_code == 409

    client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
    second_path = f"/api/v1/manufacturing-orders/{order_id}/processes/{processes[1]['id']}"
    sequence_error = client.put(second_path, json={"action": "start"})
    assert sequence_error.status_code == 409
    assert sequence_error.json()["code"] == "PROCESS_SEQUENCE_VIOLATION"
    assert client.post(f"/api/v1/manufacturing-orders/{order_id}/complete").json()["code"] == (
        "PROCESS_NOT_COMPLETED"
    )

    inactive_equipment = client.post(
        "/api/v1/masters/equipment", json={"code": "EQ-X", "name": "停止設備"}
    ).json()
    client.put(
        f"/api/v1/masters/equipment/{inactive_equipment['id']}",
        json={"code": "EQ-X", "name": "停止設備", "is_active": False},
    )
    inactive_process = client.put(
        first_path,
        json={"action": "start", "equipment_id": inactive_equipment["id"]},
    )
    assert inactive_process.status_code == 400
    assert inactive_process.json()["code"] == "BUSINESS_VALIDATION_ERROR"

    for index, process in enumerate(processes):
        path = f"/api/v1/manufacturing-orders/{order_id}/processes/{process['id']}"
        started = client.put(path, json={"action": "start"})
        assert started.status_code == 200
        assert started.json()["started_at"] is not None
        if index == 0:
            assert client.put(path, json={"action": "start"}).status_code == 409
        completed = client.put(path, json={"action": "complete", "result_note": "正常"})
        assert completed.status_code == 200
        assert completed.json()["completed_at"] is not None
        if index == 0:
            assert client.put(path, json={"action": "complete"}).status_code == 409
    completed_order = client.post(f"/api/v1/manufacturing-orders/{order_id}/complete")
    assert completed_order.status_code == 200
    assert completed_order.json()["status"] == "COMPLETED"
    assert db_session.scalar(select(ProductInventoryBalance.quantity)) == Decimal("1.000")
    assert client.put(first_path, json={"action": "start"}).status_code == 409


def test_existing_order_without_processes_keeps_phase2_completion_compatibility(
    client: TestClient, db_session: Session
) -> None:
    ids = create_master_data(client)
    receipt = receipt_payload(ids)
    receipt["lines"] = [receipt["lines"][0]]
    client.post("/api/v1/raw-material-receipts", json=receipt)
    order_id = client.post("/api/v1/manufacturing-orders", json=order_payload(ids)).json()["id"]
    client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")
    client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
    for process in db_session.scalars(
        select(ManufacturingProcess).where(ManufacturingProcess.manufacturing_order_id == order_id)
    ):
        db_session.delete(process)
    db_session.commit()

    response = client.post(f"/api/v1/manufacturing-orders/{order_id}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_equipment_edit_activation_and_historical_reference(
    client: TestClient, db_session: Session
) -> None:
    ids = create_master_data(client)
    order_id = client.post("/api/v1/manufacturing-orders", json=order_payload(ids)).json()["id"]
    changed = client.put(
        f"/api/v1/masters/equipment/{ids['equipment']}",
        json={"code": "EQ-01", "name": "蒸機更新", "is_active": False},
    )
    assert changed.status_code == 200
    assert changed.json()["is_active"] is False
    assert client.get(f"/api/v1/masters/equipment/{ids['equipment']}").json()["name"] == (
        "蒸機更新"
    )
    assert client.get(f"/api/v1/manufacturing-orders/{order_id}").status_code == 200
    rejected = client.post(
        "/api/v1/manufacturing-orders",
        json={**order_payload(ids), "order_number": "MO-P3-002"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "BUSINESS_VALIDATION_ERROR"
    duplicate = client.post("/api/v1/masters/equipment", json={"code": "EQ-01", "name": "重複"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_CODE"
