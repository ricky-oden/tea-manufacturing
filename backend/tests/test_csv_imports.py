import csv
import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.manufacturing import (
    CsvImportError,
    CsvImportJob,
    CsvImportStatus,
    Product,
    ProductInventoryBalance,
    Variety,
)
from app.services import csv_imports

HEADER = "product_code,product_name,variety_code,is_active\n"


def create_variety(client: TestClient, code: str = "V001", active: bool = True) -> int:
    response = client.post(
        "/api/v1/masters/varieties",
        json={"code": code, "name": f"品種{code}", "is_active": active},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload(client: TestClient, content: bytes, filename: str = "products.csv"):
    return client.post(
        "/api/v1/imports/products",
        files={"file": (filename, content, "text/csv")},
    )


@pytest.mark.parametrize("bom", [False, True])
def test_imports_valid_utf8_and_bom(client: TestClient, db_session: Session, bom: bool) -> None:
    variety_id = create_variety(client)
    text = HEADER + "P001,煎茶A,V001,true\nP002,煎茶B,V001,false\n\n"
    content = text.encode("utf-8-sig" if bom else "utf-8")
    response = upload(client, content)
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["total_rows"], body["success_rows"], body["error_rows"]) == (
        "SUCCEEDED",
        2,
        2,
        0,
    )
    assert body["errors"] == []
    assert body["completed_at"] is not None
    products = list(db_session.scalars(select(Product).order_by(Product.code)))
    assert [(item.code, item.name, item.variety_id, item.is_active) for item in products] == [
        ("P001", "煎茶A", variety_id, True),
        ("P002", "煎茶B", variety_id, False),
    ]
    balances = list(
        db_session.scalars(select(ProductInventoryBalance).order_by(ProductInventoryBalance.id))
    )
    assert [balance.quantity for balance in balances] == [Decimal("0.000"), Decimal("0.000")]
    detail = client.get(f"/api/v1/imports/products/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "SUCCEEDED"


@pytest.mark.parametrize(
    ("filename", "content", "code"),
    [
        ("products.txt", (HEADER + "P001,煎茶,V001,true\n").encode(), "INVALID_FILE_TYPE"),
        ("products.csv", b"\xff\xfe\xfd", "INVALID_ENCODING"),
    ],
)
def test_rejects_invalid_file_type_and_size(
    client: TestClient, filename: str, content: bytes, code: str
) -> None:
    response = upload(client, content, filename)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["import_type"] == "PRODUCT_MASTER"
    assert body["success_rows"] == 0
    assert body["errors"][0]["error_code"] == code


def test_rejects_file_over_one_mib_with_unified_413(client: TestClient) -> None:
    response = upload(client, b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.json() == {
        "code": "FILE_TOO_LARGE",
        "message": "ファイルサイズは1 MiB以下にしてください。",
        "field_errors": [],
    }


@pytest.mark.parametrize(
    "header",
    [
        "product_code,product_name,variety_code",
        "product_code,product_name,variety_code,is_active,extra",
        "code,product_name,variety_code,is_active",
        "product_name,product_code,variety_code,is_active",
    ],
)
def test_rejects_header_variants(client: TestClient, header: str) -> None:
    response = upload(client, f"{header}\nP001,煎茶,V001,true\n".encode())
    assert response.status_code == 200
    assert response.json()["errors"][0]["error_code"] == "INVALID_HEADER"


@pytest.mark.parametrize(
    ("content", "code", "total_rows"),
    [
        (HEADER.encode(), "EMPTY_FILE", 0),
        ((HEADER + "P001,煎茶,V001,true\n\nP002,玉露,V001,true\n").encode(), "EMPTY_ROW", 3),
        (
            (HEADER + "".join(f"P{i:04d},製品{i},V001,true\n" for i in range(1001))).encode(),
            "TOO_MANY_ROWS",
            1001,
        ),
    ],
)
def test_rejects_empty_intermediate_blank_and_row_limit(
    client: TestClient, content: bytes, code: str, total_rows: int
) -> None:
    response = upload(client, content)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["total_rows"] == total_rows
    assert code in {error["error_code"] for error in body["errors"]}


@pytest.mark.parametrize(
    "row",
    [
        ",煎茶,V001,true",
        "P001,,V001,true",
        "P001,煎茶,,true",
        "P001,煎茶,V001,",
    ],
)
def test_rejects_required_values(client: TestClient, row: str) -> None:
    create_variety(client)
    response = upload(client, (HEADER + row + "\n").encode())
    assert response.status_code == 200
    assert "REQUIRED" in {error["error_code"] for error in response.json()["errors"]}


@pytest.mark.parametrize(
    ("row", "field_name", "code"),
    [
        (f"{'P' * 31},煎茶,V001,true", "product_code", "MAX_LENGTH"),
        (f"P001,{'茶' * 101},V001,true", "product_name", "MAX_LENGTH"),
        ("P001,煎茶,V001,TRUE", "is_active", "INVALID_FORMAT"),
    ],
)
def test_rejects_lengths_and_active_format(
    client: TestClient, row: str, field_name: str, code: str
) -> None:
    create_variety(client)
    response = upload(client, (HEADER + row + "\n").encode())
    errors = response.json()["errors"]
    assert any(
        error["field_name"] == field_name and error["error_code"] == code for error in errors
    )


def test_collects_duplicate_and_reference_errors(client: TestClient, db_session: Session) -> None:
    create_variety(client, "V001")
    inactive_id = create_variety(client, "V002", active=False)
    existing = Product(code="EXISTING", name="登録済み", variety_id=inactive_id, is_active=True)
    db_session.add(existing)
    db_session.flush()
    db_session.add(ProductInventoryBalance(product_id=existing.id, quantity=Decimal("0.000")))
    db_session.commit()
    content = (
        HEADER
        + "DUP,重複1,V001,true\n"
        + "DUP,重複2,V001,true\n"
        + "EXISTING,既存,V001,true\n"
        + "MISSING,品種なし,V999,true\n"
        + "INACTIVE,無効品種,V002,true\n"
    ).encode()
    response = upload(client, content)
    assert response.status_code == 200
    body = response.json()
    codes = [error["error_code"] for error in body["errors"]]
    assert codes.count("DUPLICATE_IN_FILE") == 2
    assert "DUPLICATE_IN_DATABASE" in codes
    assert "REFERENCE_NOT_FOUND" in codes
    assert "REFERENCE_INACTIVE" in codes
    assert body["status"] == "FAILED"
    assert body["success_rows"] == 0
    assert body["error_rows"] == 5
    assert db_session.scalar(select(func.count()).select_from(Product)) == 1
    assert db_session.scalar(select(func.count()).select_from(ProductInventoryBalance)) == 1


def test_one_error_registers_no_products_or_balances(
    client: TestClient, db_session: Session
) -> None:
    create_variety(client)
    response = upload(client, (HEADER + "P001,正常,V001,true\nP002,不正,V001,yes\n").encode())
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["total_rows"], body["success_rows"], body["error_rows"]) == (
        "FAILED",
        2,
        0,
        1,
    )
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0
    assert db_session.scalar(select(func.count()).select_from(ProductInventoryBalance)) == 0
    assert db_session.scalar(select(func.count()).select_from(CsvImportJob)) == 1
    assert db_session.scalar(select(func.count()).select_from(CsvImportError)) == 1


def test_database_exception_rolls_back_products_and_saves_safe_error(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_variety(client)

    def flush_then_fail(
        session: Session,
        job: CsvImportJob,
        rows: list[csv_imports.ParsedProductRow],
        varieties: dict[str, Variety],
    ) -> None:
        product = Product(
            code=rows[0].product_code,
            name=rows[0].product_name,
            variety_id=varieties[rows[0].variety_code].id,
            is_active=True,
        )
        session.add(product)
        session.flush()
        session.add(ProductInventoryBalance(product_id=product.id, quantity=Decimal("0.000")))
        session.flush()
        raise RuntimeError("phase5-sensitive-database-error")

    monkeypatch.setattr(csv_imports, "_save_products", flush_then_fail)
    response = upload(client, (HEADER + "P001,煎茶,V001,true\n").encode())
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert "phase5-sensitive-database-error" not in response.text
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0
    assert db_session.scalar(select(func.count()).select_from(ProductInventoryBalance)) == 0
    job = db_session.scalar(select(CsvImportJob).order_by(CsvImportJob.id.desc()))
    assert job.status == CsvImportStatus.FAILED
    assert (job.total_rows, job.success_rows, job.error_rows) == (1, 0, 1)
    error = db_session.scalar(
        select(CsvImportError).where(CsvImportError.csv_import_job_id == job.id)
    )
    assert error.error_code == "DATABASE_ERROR"
    assert "phase5-sensitive" not in error.error_message


def test_error_csv_has_five_columns_and_escapes_values(
    client: TestClient,
) -> None:
    create_variety(client)
    value = 'bad,"quoted"\nvalue'
    source = io.StringIO(newline="")
    writer = csv.writer(source, lineterminator="\n")
    writer.writerow(["product_code", "product_name", "variety_code", "is_active"])
    writer.writerow(["P001", "煎茶", "V001", value])
    result = upload(client, source.getvalue().encode()).json()
    response = client.get(f"/api/v1/imports/products/{result['id']}/errors.csv")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8"), newline="")))
    assert rows[0] == ["row_number", "field_name", "error_code", "error_message", "input_value"]
    assert all(len(row) == 5 for row in rows)
    assert rows[1][0] == "2"
    assert rows[1][4] == value


def test_missing_file_and_missing_job_use_unified_errors(client: TestClient) -> None:
    missing_file = client.post("/api/v1/imports/products")
    assert missing_file.status_code == 422
    assert set(missing_file.json()) == {"code", "message", "field_errors"}
    missing_job = client.get("/api/v1/imports/products/999999")
    assert missing_job.status_code == 404
    assert missing_job.json()["code"] == "NOT_FOUND"


def test_success_job_has_no_error_csv(client: TestClient) -> None:
    create_variety(client)
    result = upload(client, (HEADER + "P001,煎茶,V001,true\n").encode()).json()
    response = client.get(f"/api/v1/imports/products/{result['id']}/errors.csv")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
