from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.manufacturing import (
    InventoryKind,
    InventoryTransaction,
    InventoryTransactionType,
    ManufacturingOrder,
    ManufacturingStatus,
    Product,
    ProductInventoryBalance,
    RawMaterialInventoryBalance,
    Shipment,
    ShipmentLine,
    ShipmentStatus,
)


def master_data(client: TestClient) -> dict[str, int]:
    tea = client.post("/api/v1/masters/tea-leaves", json={"code": "TL-01", "name": "煎茶"}).json()
    variety = client.post(
        "/api/v1/masters/varieties", json={"code": "V-01", "name": "やぶきた"}
    ).json()
    supplier = client.post(
        "/api/v1/masters/suppliers", json={"code": "S-01", "name": "茶園A"}
    ).json()
    equipment = client.post(
        "/api/v1/masters/equipment", json={"code": "EQ-01", "name": "蒸機"}
    ).json()
    products = []
    for index in range(1, 4):
        products.append(
            client.post(
                "/api/v1/masters/products",
                json={
                    "code": f"P-{index:02d}",
                    "name": f"製品{index}",
                    "variety_id": variety["id"],
                },
            ).json()["id"]
        )
    return {
        "tea": tea["id"],
        "variety": variety["id"],
        "supplier": supplier["id"],
        "equipment": equipment["id"],
        "product1": products[0],
        "product2": products[1],
        "product3": products[2],
    }


def set_product_balances(session: Session, quantities: dict[int, str]) -> None:
    for product_id, quantity in quantities.items():
        balance = session.scalar(
            select(ProductInventoryBalance).where(ProductInventoryBalance.product_id == product_id)
        )
        balance.quantity = Decimal(quantity)
    session.commit()


def shipment_payload(ids: dict[str, int], number: str = "SH-0001") -> dict:
    return {
        "shipment_number": number,
        "shipped_date": "2026-08-12",
        "lines": [
            {"product_id": ids["product1"], "quantity": "2.000"},
            {"product_id": ids["product2"], "quantity": "1.500"},
        ],
    }


def test_inventory_balance_lists_paging_and_no_write_api(
    client: TestClient, db_session: Session
) -> None:
    ids = master_data(client)
    set_product_balances(
        db_session,
        {ids["product1"]: "1.000", ids["product2"]: "2.000", ids["product3"]: "3.000"},
    )
    db_session.add(
        RawMaterialInventoryBalance(
            tea_leaf_id=ids["tea"], variety_id=ids["variety"], quantity=Decimal("4.000")
        )
    )
    db_session.commit()

    raw = client.get("/api/v1/inventories/raw-materials?page=1&page_size=2").json()
    assert (raw["total"], len(raw["items"]), raw["items"][0]["unit"]) == (1, 1, "kg")
    first = client.get("/api/v1/inventories/products?page=1&page_size=2").json()
    second = client.get("/api/v1/inventories/products?page=2&page_size=2").json()
    assert (first["total"], first["total_pages"], len(first["items"])) == (3, 2, 2)
    assert len(second["items"]) == 1
    assert {item["id"] for item in first["items"]}.isdisjoint(
        {item["id"] for item in second["items"]}
    )
    for method in (client.post, client.put, client.patch, client.delete):
        assert method("/api/v1/inventories/products").status_code in {404, 405}


def test_inventory_transaction_search_filters(client: TestClient, db_session: Session) -> None:
    ids = master_data(client)
    transactions = [
        InventoryTransaction(
            inventory_kind=InventoryKind.RAW_MATERIAL,
            transaction_type=InventoryTransactionType.RECEIPT,
            tea_leaf_id=ids["tea"],
            variety_id=ids["variety"],
            quantity_delta=Decimal("2.000"),
            balance_after=Decimal("2.000"),
            reference_type="TEST",
            reference_id=1,
            occurred_at=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        ),
        InventoryTransaction(
            inventory_kind=InventoryKind.PRODUCT,
            transaction_type=InventoryTransactionType.MANUFACTURING_OUTPUT,
            product_id=ids["product1"],
            quantity_delta=Decimal("3.000"),
            balance_after=Decimal("3.000"),
            reference_type="TEST",
            reference_id=2,
            occurred_at=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
        ),
    ]
    db_session.add_all(transactions)
    db_session.commit()
    filters = [
        f"inventory_kind=RAW_MATERIAL&tea_leaf_id={ids['tea']}&variety_id={ids['variety']}",
        f"inventory_kind=PRODUCT&product_id={ids['product1']}",
        "transaction_type=RECEIPT",
        "date_from=2026-08-12&date_to=2026-08-12",
    ]
    for query in filters:
        result = client.get(f"/api/v1/inventory-transactions?page=1&page_size=20&{query}")
        assert result.status_code == 200
        assert result.json()["total"] == 1
    invalid = client.get("/api/v1/inventory-transactions?date_from=2026-08-13&date_to=2026-08-12")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_shipment_draft_list_detail_edit_and_validation(
    client: TestClient, db_session: Session
) -> None:
    ids = master_data(client)
    created = client.post("/api/v1/shipments", json=shipment_payload(ids))
    assert created.status_code == 201
    assert created.json()["status"] == "DRAFT"
    shipment_id = created.json()["id"]
    assert client.get("/api/v1/shipments?page=1&page_size=20").json()["total"] == 1
    assert client.get(f"/api/v1/shipments/{shipment_id}").status_code == 200
    edited_payload = shipment_payload(ids)
    edited_payload["shipped_date"] = "2026-08-13"
    edited_payload["lines"] = [edited_payload["lines"][0]]
    edited = client.put(f"/api/v1/shipments/{shipment_id}", json=edited_payload)
    assert edited.status_code == 200
    assert edited.json()["shipped_date"] == "2026-08-13"
    duplicate = client.post("/api/v1/shipments", json=shipment_payload(ids))
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_SHIPMENT_NUMBER"
    repeated = shipment_payload(ids, "SH-0002")
    repeated["lines"] = [repeated["lines"][0], repeated["lines"][0]]
    assert client.post("/api/v1/shipments", json=repeated).status_code == 422
    invalid = shipment_payload(ids, "SH-0003")
    invalid["lines"][0]["quantity"] = "0"
    invalid_response = client.post("/api/v1/shipments", json=invalid)
    assert invalid_response.status_code == 422
    assert set(invalid_response.json()) == {"code", "message", "field_errors"}
    product = db_session.get(Product, ids["product3"])
    product.is_active = False
    db_session.commit()
    inactive = shipment_payload(ids, "SH-0004")
    inactive["lines"] = [{"product_id": ids["product3"], "quantity": "1.000"}]
    inactive_response = client.post("/api/v1/shipments", json=inactive)
    assert inactive_response.status_code == 400
    assert inactive_response.json()["code"] == "BUSINESS_VALIDATION_ERROR"
    db_session.add(
        Shipment(
            shipment_number="SH-DB",
            shipped_date=date(2026, 8, 12),
            lines=[ShipmentLine(product_id=ids["product1"], quantity=Decimal("0.000"))],
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confirm_multiple_lines_updates_inventory_history_and_read_only(
    client: TestClient, db_session: Session
) -> None:
    ids = master_data(client)
    set_product_balances(db_session, {ids["product1"]: "10.000", ids["product2"]: "5.000"})
    shipment_id = client.post("/api/v1/shipments", json=shipment_payload(ids)).json()["id"]
    confirmed = client.post(f"/api/v1/shipments/{shipment_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"
    assert confirmed.json()["confirmed_at"] is not None
    db_session.expire_all()
    balances = list(
        db_session.scalars(
            select(ProductInventoryBalance)
            .where(ProductInventoryBalance.product_id.in_([ids["product1"], ids["product2"]]))
            .order_by(ProductInventoryBalance.product_id)
        )
    )
    assert [item.quantity for item in balances] == [Decimal("8.000"), Decimal("3.500")]
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 2
    assert client.post(f"/api/v1/shipments/{shipment_id}/confirm").status_code == 409
    assert (
        client.put(f"/api/v1/shipments/{shipment_id}", json=shipment_payload(ids)).status_code
        == 409
    )


def test_insufficient_inventory_rolls_back_all_lines(
    client: TestClient, db_session: Session
) -> None:
    ids = master_data(client)
    set_product_balances(db_session, {ids["product1"]: "10.000", ids["product2"]: "1.000"})
    shipment_id = client.post("/api/v1/shipments", json=shipment_payload(ids)).json()["id"]
    response = client.post(f"/api/v1/shipments/{shipment_id}/confirm")
    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_PRODUCT_INVENTORY"
    db_session.expire_all()
    assert db_session.get(Shipment, shipment_id).status == ShipmentStatus.DRAFT
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 0
    balances = {
        item.product_id: item.quantity
        for item in db_session.scalars(
            select(ProductInventoryBalance).where(
                ProductInventoryBalance.product_id.in_([ids["product1"], ids["product2"]])
            )
        )
    }
    assert balances == {
        ids["product1"]: Decimal("10.000"),
        ids["product2"]: Decimal("1.000"),
    }


def test_forced_exception_rolls_back_confirmation(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = master_data(client)
    set_product_balances(db_session, {ids["product1"]: "10.000", ids["product2"]: "5.000"})
    shipment_id = client.post("/api/v1/shipments", json=shipment_payload(ids)).json()["id"]

    def flush_then_fail(session: Session) -> None:
        session.flush()
        raise RuntimeError("phase4-sensitive-error")

    monkeypatch.setattr(Session, "commit", flush_then_fail)
    response = client.post(f"/api/v1/shipments/{shipment_id}/confirm")
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert "phase4-sensitive-error" not in response.text
    db_session.expire_all()
    assert db_session.get(Shipment, shipment_id).status == ShipmentStatus.DRAFT
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 0
    balances = {
        item.product_id: item.quantity
        for item in db_session.scalars(
            select(ProductInventoryBalance).where(
                ProductInventoryBalance.product_id.in_([ids["product1"], ids["product2"]])
            )
        )
    }
    assert balances == {
        ids["product1"]: Decimal("10.000"),
        ids["product2"]: Decimal("5.000"),
    }


def test_concurrent_confirmation_processes_once(client: TestClient, db_session: Session) -> None:
    ids = master_data(client)
    set_product_balances(db_session, {ids["product1"]: "10.000", ids["product2"]: "5.000"})
    shipment_id = client.post("/api/v1/shipments", json=shipment_payload(ids)).json()["id"]
    barrier = Barrier(3, timeout=5)

    def confirm() -> tuple[int, str]:
        with TestClient(create_app(), raise_server_exceptions=False) as concurrent_client:
            barrier.wait()
            response = concurrent_client.post(f"/api/v1/shipments/{shipment_id}/confirm")
            return response.status_code, response.json().get("code", "")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(confirm) for _ in range(2)]
        barrier.wait()
        results = [future.result(timeout=10) for future in futures]
    assert sorted(status for status, _ in results) == [200, 409]
    assert next(code for status, code in results if status == 409) == "SHIPMENT_ALREADY_CONFIRMED"
    db_session.expire_all()
    assert db_session.get(Shipment, shipment_id).status == ShipmentStatus.CONFIRMED
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 2
    balances = {
        item.product_id: item.quantity
        for item in db_session.scalars(
            select(ProductInventoryBalance).where(
                ProductInventoryBalance.product_id.in_([ids["product1"], ids["product2"]])
            )
        )
    }
    assert balances == {
        ids["product1"]: Decimal("8.000"),
        ids["product2"]: Decimal("3.500"),
    }


def test_summary_boundaries_breakdowns_unconfirmed_exclusion_and_dashboard(
    client: TestClient, db_session: Session
) -> None:
    ids = master_data(client)
    receipt = {
        "receipt_number": "RC-P4",
        "received_date": "2026-08-12",
        "supplier_id": ids["supplier"],
        "lines": [
            {
                "tea_leaf_id": ids["tea"],
                "variety_id": ids["variety"],
                "quantity": "5.000",
            }
        ],
    }
    client.post("/api/v1/raw-material-receipts", json=receipt)
    set_product_balances(db_session, {ids["product1"]: "10.000"})
    db_session.add(
        ManufacturingOrder(
            order_number="MO-SUM",
            product_id=ids["product1"],
            planned_quantity=Decimal("4.000"),
            planned_date=date(2026, 8, 12),
            equipment_id=ids["equipment"],
            status=ManufacturingStatus.COMPLETED,
            completed_at=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        )
    )
    db_session.commit()
    confirmed_payload = shipment_payload(ids, "SH-SUM-1")
    confirmed_payload["lines"] = [{"product_id": ids["product1"], "quantity": "2.000"}]
    confirmed_id = client.post("/api/v1/shipments", json=confirmed_payload).json()["id"]
    client.post(f"/api/v1/shipments/{confirmed_id}/confirm")
    draft_payload = shipment_payload(ids, "SH-SUM-2")
    draft_payload["lines"] = [{"product_id": ids["product1"], "quantity": "3.000"}]
    client.post("/api/v1/shipments", json=draft_payload)

    summary = client.get("/api/v1/reports/summary?date_from=2026-08-12&date_to=2026-08-12")
    assert summary.status_code == 200
    body = summary.json()
    assert (
        body["receipt_quantity"],
        body["manufacturing_quantity"],
        body["shipment_quantity"],
    ) == (
        5.0,
        4.0,
        2.0,
    )
    assert len(body["receipt_breakdown"]) == 1
    assert len(body["manufacturing_breakdown"]) == 1
    assert len(body["shipment_breakdown"]) == 1
    dashboard = client.get("/api/v1/dashboard?date_from=2026-08-12&date_to=2026-08-12").json()
    assert dashboard["manufacturing_status_counts"]["COMPLETED"] == 1
    assert dashboard["receipt_quantity"] == body["receipt_quantity"]
    assert dashboard["manufacturing_quantity"] == body["manufacturing_quantity"]
    assert dashboard["shipment_quantity"] == body["shipment_quantity"]
    invalid = client.get("/api/v1/reports/summary?date_from=2026-08-13&date_to=2026-08-12")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"
