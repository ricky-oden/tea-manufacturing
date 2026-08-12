from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.seed import seed_demo_data
from app.models.manufacturing import Product, ProductInventoryBalance, TeaLeaf


def create_masters(client: TestClient) -> dict[str, dict]:
    tea = client.post("/api/v1/masters/tea-leaves", json={"code": "TL-01", "name": "煎茶"}).json()
    variety = client.post(
        "/api/v1/masters/varieties", json={"code": "VR-01", "name": "やぶきた"}
    ).json()
    supplier = client.post(
        "/api/v1/masters/suppliers", json={"code": "SP-01", "name": "茶園"}
    ).json()
    equipment = client.post(
        "/api/v1/masters/equipment", json={"code": "EQ-01", "name": "蒸機"}
    ).json()
    product = client.post(
        "/api/v1/masters/products",
        json={"code": "PR-01", "name": "煎茶製品", "variety_id": variety["id"]},
    ).json()
    return {
        "tea": tea,
        "variety": variety,
        "supplier": supplier,
        "equipment": equipment,
        "product": product,
    }


def order_payload(masters: dict[str, dict], number: str = "MO-01") -> dict:
    return {
        "order_number": number,
        "product_id": masters["product"]["id"],
        "planned_quantity": "2.500",
        "planned_date": "2026-08-12",
        "equipment_id": masters["equipment"]["id"],
        "materials": [
            {
                "tea_leaf_id": masters["tea"]["id"],
                "variety_id": masters["variety"]["id"],
                "planned_quantity": "3.000",
            }
        ],
    }


def test_all_masters_support_paged_crud_and_no_delete(client: TestClient) -> None:
    masters = create_masters(client)
    resources = {
        "products": masters["product"],
        "tea-leaves": masters["tea"],
        "varieties": masters["variety"],
        "suppliers": masters["supplier"],
        "equipment": masters["equipment"],
    }
    for resource, created in resources.items():
        listing = client.get(f"/api/v1/masters/{resource}?page=1&page_size=1")
        assert listing.status_code == 200
        assert set(listing.json()) == {"items", "page", "page_size", "total", "total_pages"}
        assert listing.json()["total"] == 1
        detail = client.get(f"/api/v1/masters/{resource}/{created['id']}")
        assert detail.status_code == 200
        body = {**created, "name": f"{created['name']}更新", "is_active": False}
        body.pop("id", None)
        duplicate = client.post(f"/api/v1/masters/{resource}", json=body)
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "DUPLICATE_CODE"
        updated = client.put(f"/api/v1/masters/{resource}/{created['id']}", json=body)
        assert updated.status_code == 200
        assert updated.json()["is_active"] is False
        assert client.delete(f"/api/v1/masters/{resource}/{created['id']}").status_code == 405


def test_paging_contract_rejects_invalid_values_for_every_paged_api(client: TestClient) -> None:
    paths = [
        "/api/v1/manufacturing-orders",
        "/api/v1/raw-material-receipts",
        "/api/v1/inventories/raw-materials",
        "/api/v1/inventories/products",
        "/api/v1/inventory-transactions",
        "/api/v1/shipments",
        "/api/v1/masters/tea-leaves",
        "/api/v1/masters/varieties",
        "/api/v1/masters/suppliers",
        "/api/v1/masters/equipment",
        "/api/v1/masters/products",
    ]
    for path in paths:
        for query in ("page=0", "page_size=101"):
            response = client.get(f"{path}?{query}")
            assert response.status_code == 422
            assert response.json()["code"] == "VALIDATION_ERROR"


def test_draft_order_can_be_edited_filtered_and_has_complete_detail(client: TestClient) -> None:
    masters = create_masters(client)
    created = client.post("/api/v1/manufacturing-orders", json=order_payload(masters)).json()
    changed = order_payload(masters, "MO-EDITED")
    changed["planned_quantity"] = "4.000"
    updated = client.put(f"/api/v1/manufacturing-orders/{created['id']}", json=changed)
    assert updated.status_code == 200
    assert updated.json()["order_number"] == "MO-EDITED"
    assert updated.json()["materials"][0]["tea_leaf_name"] == "煎茶"
    assert updated.json()["equipment_name"] == "蒸機"
    assert updated.json()["processes"] == []
    assert updated.json()["inventory_transactions"] == []
    listing = client.get(
        "/api/v1/manufacturing-orders",
        params={
            "status": "DRAFT",
            "product_id": masters["product"]["id"],
            "planned_date_from": "2026-08-12",
            "planned_date_to": "2026-08-12",
        },
    )
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == created["id"]


def test_non_draft_order_edit_is_rejected_without_change(client: TestClient) -> None:
    masters = create_masters(client)
    created = client.post("/api/v1/manufacturing-orders", json=order_payload(masters)).json()
    client.post(f"/api/v1/manufacturing-orders/{created['id']}/issue")
    changed = order_payload(masters, "MO-CHANGED")
    response = client.put(f"/api/v1/manufacturing-orders/{created['id']}", json=changed)
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"
    detail = client.get(f"/api/v1/manufacturing-orders/{created['id']}").json()
    assert detail["order_number"] == "MO-01"


def test_inactive_masters_reject_new_use_but_past_references_remain(client: TestClient) -> None:
    masters = create_masters(client)
    order = client.post("/api/v1/manufacturing-orders", json=order_payload(masters)).json()
    receipt_payload = {
        "receipt_number": "RC-01",
        "received_date": "2026-08-12",
        "supplier_id": masters["supplier"]["id"],
        "lines": [
            {
                "tea_leaf_id": masters["tea"]["id"],
                "variety_id": masters["variety"]["id"],
                "quantity": "1.000",
            }
        ],
    }
    receipt = client.post("/api/v1/raw-material-receipts", json=receipt_payload).json()
    supplier_payload = {**masters["supplier"], "is_active": False}
    supplier_payload.pop("id")
    assert (
        client.put(
            f"/api/v1/masters/suppliers/{masters['supplier']['id']}", json=supplier_payload
        ).status_code
        == 200
    )
    rejected_receipt = client.post(
        "/api/v1/raw-material-receipts", json={**receipt_payload, "receipt_number": "RC-02"}
    )
    assert rejected_receipt.status_code == 400
    assert rejected_receipt.json()["code"] == "BUSINESS_VALIDATION_ERROR"
    assert client.get(f"/api/v1/raw-material-receipts/{receipt['id']}").status_code == 200
    for resource, key in (
        ("tea-leaves", "tea"),
        ("varieties", "variety"),
        ("equipment", "equipment"),
        ("products", "product"),
    ):
        current = masters[key]
        payload = {**current, "is_active": False}
        payload.pop("id", None)
        response = client.put(f"/api/v1/masters/{resource}/{current['id']}", json=payload)
        assert response.status_code == 200
    rejected = client.post("/api/v1/manufacturing-orders", json=order_payload(masters, "MO-02"))
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "BUSINESS_VALIDATION_ERROR"
    detail = client.get(f"/api/v1/manufacturing-orders/{order['id']}")
    assert detail.status_code == 200
    assert detail.json()["product_name"] == "煎茶製品"


def test_invalid_order_filter_period_is_unified_validation(client: TestClient) -> None:
    response = client.get(
        "/api/v1/manufacturing-orders?planned_date_from=2026-08-13&planned_date_to=2026-08-12"
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_demo_seed_is_idempotent(db_session: Session) -> None:
    seed_demo_data()
    seed_demo_data()
    db_session.expire_all()
    assert (
        db_session.scalar(
            select(func.count()).select_from(TeaLeaf).where(TeaLeaf.code == "TL-DEMO")
        )
        == 1
    )
    product_id = db_session.scalar(select(Product.id).where(Product.code == "PR-DEMO"))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(ProductInventoryBalance)
            .where(ProductInventoryBalance.product_id == product_id)
        )
        == 1
    )
