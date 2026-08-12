from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.manufacturing import (
    InventoryTransaction,
    ManufacturingOrder,
    ProductInventoryBalance,
    RawMaterialInventoryBalance,
)


def masters(client: TestClient) -> dict[str, int]:
    tea = client.post("/api/v1/masters/tea-leaves", json={"code": "TL-01", "name": "煎茶"}).json()
    variety = client.post(
        "/api/v1/masters/varieties", json={"code": "V-01", "name": "やぶきた"}
    ).json()
    equipment = client.post(
        "/api/v1/masters/equipment", json={"code": "EQ-01", "name": "蒸機"}
    ).json()
    product = client.post(
        "/api/v1/masters/products",
        json={"code": "P-01", "name": "煎茶製品", "variety_id": variety["id"]},
    ).json()
    return {
        "tea": tea["id"],
        "variety": variety["id"],
        "equipment": equipment["id"],
        "product": product["id"],
    }


def payload(ids: dict[str, int], quantity: str = "2.500") -> dict:
    return {
        "order_number": "MO-0001",
        "product_id": ids["product"],
        "planned_quantity": quantity,
        "planned_date": "2026-08-12",
        "equipment_id": ids["equipment"],
        "materials": [
            {"tea_leaf_id": ids["tea"], "variety_id": ids["variety"], "planned_quantity": "3.000"}
        ],
    }


def add_balance(session: Session, ids: dict[str, int], quantity: str) -> None:
    session.add(
        RawMaterialInventoryBalance(
            tea_leaf_id=ids["tea"], variety_id=ids["variety"], quantity=Decimal(quantity)
        )
    )
    session.commit()


def create_order_in_status(
    client: TestClient,
    db_session: Session,
    target_status: str,
) -> tuple[dict[str, int], int]:
    ids = masters(client)
    add_balance(db_session, ids, "10.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    if target_status == "CANCELLED":
        client.post(f"/api/v1/manufacturing-orders/{order_id}/cancel")
        return ids, order_id
    if target_status in {"ISSUED", "IN_PROGRESS", "COMPLETED"}:
        client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")
    if target_status in {"IN_PROGRESS", "COMPLETED"}:
        client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
    if target_status == "COMPLETED":
        client.post(f"/api/v1/manufacturing-orders/{order_id}/complete")
    return ids, order_id


def inventory_snapshot(session: Session) -> tuple[Decimal, Decimal, int]:
    session.expire_all()
    raw = session.scalar(select(RawMaterialInventoryBalance.quantity)) or Decimal("0.000")
    product = session.scalar(select(ProductInventoryBalance.quantity)) or Decimal("0.000")
    history_count = session.scalar(select(func.count()).select_from(InventoryTransaction)) or 0
    return raw, product, history_count


def test_create_list_and_detail_order(client: TestClient) -> None:
    ids = masters(client)
    created = client.post("/api/v1/manufacturing-orders", json=payload(ids))
    assert created.status_code == 201
    assert created.json()["status"] == "DRAFT"
    listing = client.get("/api/v1/manufacturing-orders?page=1&page_size=20")
    assert listing.json()["total"] == 1
    assert listing.json()["total_pages"] == 1
    assert (
        client.get(f"/api/v1/manufacturing-orders/{created.json()['id']}").json()["order_number"]
        == "MO-0001"
    )


def test_quantity_requires_positive_three_decimal_precision(client: TestClient) -> None:
    ids = masters(client)
    for invalid in ["0", "-0.001", "1.0001"]:
        response = client.post("/api/v1/manufacturing-orders", json=payload(ids, invalid))
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_manufacturing_flow_updates_balances_and_history(
    client: TestClient, db_session: Session
) -> None:
    ids = masters(client)
    add_balance(db_session, ids, "10.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    assert (
        client.post(f"/api/v1/manufacturing-orders/{order_id}/issue").json()["status"] == "ISSUED"
    )
    assert (
        client.post(f"/api/v1/manufacturing-orders/{order_id}/start").json()["status"]
        == "IN_PROGRESS"
    )
    assert (
        client.post(f"/api/v1/manufacturing-orders/{order_id}/complete").json()["status"]
        == "COMPLETED"
    )
    db_session.expire_all()
    assert db_session.scalar(select(RawMaterialInventoryBalance.quantity)) == Decimal("7.000")
    assert db_session.scalar(select(ProductInventoryBalance.quantity)) == Decimal("2.500")
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 2


def test_insufficient_material_rolls_back(client: TestClient, db_session: Session) -> None:
    ids = masters(client)
    add_balance(db_session, ids, "1.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")
    response = client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_RAW_MATERIAL"
    assert client.get(f"/api/v1/manufacturing-orders/{order_id}").json()["status"] == "ISSUED"
    db_session.expire_all()
    assert db_session.scalar(select(RawMaterialInventoryBalance.quantity)) == Decimal("1.000")


def test_double_start_and_complete_do_not_repeat_inventory(
    client: TestClient, db_session: Session
) -> None:
    ids = masters(client)
    add_balance(db_session, ids, "10.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")
    client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
    assert client.post(f"/api/v1/manufacturing-orders/{order_id}/start").status_code == 409
    client.post(f"/api/v1/manufacturing-orders/{order_id}/complete")
    assert client.post(f"/api/v1/manufacturing-orders/{order_id}/complete").status_code == 409
    db_session.expire_all()
    assert db_session.scalar(select(ProductInventoryBalance.quantity)) == Decimal("2.500")
    assert db_session.scalar(select(func.count()).select_from(InventoryTransaction)) == 2


def test_forced_exception_rolls_back_start_transaction(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = masters(client)
    add_balance(db_session, ids, "10.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")

    def flush_then_fail(session: Session) -> None:
        session.flush()
        raise RuntimeError("forced-sensitive-transaction-error")

    monkeypatch.setattr(Session, "commit", flush_then_fail)
    response = client.post(f"/api/v1/manufacturing-orders/{order_id}/start")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "サーバー内部でエラーが発生しました。",
        "field_errors": [],
    }
    assert "forced-sensitive-transaction-error" not in response.text
    db_session.expire_all()
    assert db_session.get(ManufacturingOrder, order_id).status == "ISSUED"
    assert inventory_snapshot(db_session) == (Decimal("10.000"), Decimal("0.000"), 0)


def test_concurrent_start_processes_inventory_once(client: TestClient, db_session: Session) -> None:
    ids = masters(client)
    add_balance(db_session, ids, "10.000")
    order_id = client.post("/api/v1/manufacturing-orders", json=payload(ids)).json()["id"]
    client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")
    start_barrier = Barrier(3, timeout=5)

    def request_start() -> tuple[int, dict]:
        with TestClient(create_app(), raise_server_exceptions=False) as concurrent_client:
            start_barrier.wait()
            response = concurrent_client.post(f"/api/v1/manufacturing-orders/{order_id}/start")
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(request_start) for _ in range(2)]
        start_barrier.wait()
        results = [future.result(timeout=10) for future in futures]

    assert sorted(status for status, _ in results) == [200, 409]
    rejected = next(body for status, body in results if status == 409)
    assert rejected["code"] == "INVALID_STATUS_TRANSITION"
    db_session.expire_all()
    assert db_session.get(ManufacturingOrder, order_id).status == "IN_PROGRESS"
    assert inventory_snapshot(db_session) == (Decimal("7.000"), Decimal("0.000"), 1)


@pytest.mark.parametrize("initial_status", ["DRAFT", "ISSUED"])
def test_cancel_is_allowed_without_inventory_change(
    client: TestClient, db_session: Session, initial_status: str
) -> None:
    _, order_id = create_order_in_status(client, db_session, initial_status)
    before = inventory_snapshot(db_session)
    response = client.post(f"/api/v1/manufacturing-orders/{order_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert inventory_snapshot(db_session) == before


@pytest.mark.parametrize(
    ("initial_status", "action"),
    [
        ("DRAFT", "start"),
        ("DRAFT", "complete"),
        ("ISSUED", "complete"),
        ("IN_PROGRESS", "issue"),
        ("IN_PROGRESS", "cancel"),
        ("COMPLETED", "complete"),
        ("CANCELLED", "issue"),
    ],
)
def test_invalid_status_transition_changes_nothing(
    client: TestClient,
    db_session: Session,
    initial_status: str,
    action: str,
) -> None:
    _, order_id = create_order_in_status(client, db_session, initial_status)
    before = inventory_snapshot(db_session)

    response = client.post(f"/api/v1/manufacturing-orders/{order_id}/{action}")

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"
    assert client.get(f"/api/v1/manufacturing-orders/{order_id}").json()["status"] == initial_status
    assert inventory_snapshot(db_session) == before


def test_order_pagination_filter_and_validation(client: TestClient) -> None:
    ids = masters(client)
    order_ids: list[int] = []
    for index in range(1, 6):
        order_payload = payload(ids)
        order_payload["order_number"] = f"MO-{index:04d}"
        order_ids.append(
            client.post("/api/v1/manufacturing-orders", json=order_payload).json()["id"]
        )
    for order_id in order_ids[:2]:
        client.post(f"/api/v1/manufacturing-orders/{order_id}/issue")

    first = client.get("/api/v1/manufacturing-orders?page=1&page_size=2").json()
    second = client.get("/api/v1/manufacturing-orders?page=2&page_size=2").json()
    assert (len(first["items"]), first["total"], first["total_pages"]) == (2, 5, 3)
    assert (len(second["items"]), second["total"], second["total_pages"]) == (2, 5, 3)
    assert {item["id"] for item in first["items"]}.isdisjoint(
        {item["id"] for item in second["items"]}
    )

    filtered = client.get("/api/v1/manufacturing-orders?page=1&page_size=2&status=ISSUED").json()
    assert filtered["total"] == 2
    assert filtered["total_pages"] == 1
    assert len(filtered["items"]) == 2
    assert {item["status"] for item in filtered["items"]} == {"ISSUED"}

    for query in ["page=0&page_size=2", "page=1&page_size=101"]:
        response = client.get(f"/api/v1/manufacturing-orders?{query}")
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
