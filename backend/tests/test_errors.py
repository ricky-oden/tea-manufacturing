from fastapi import Query
from fastapi.testclient import TestClient

from app.core.errors import ConflictError
from app.main import create_app


def test_validation_error_uses_unified_shape() -> None:
    application = create_app()

    @application.get("/api/v1/test/validation")
    def validation_route(quantity: int = Query(gt=0)) -> dict[str, int]:
        return {"quantity": quantity}

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test/validation", params={"quantity": 0})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["message"] == "入力内容を確認してください。"
    assert response.json()["field_errors"]


def test_not_found_uses_unified_shape(client: TestClient) -> None:
    response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "code": "NOT_FOUND",
        "message": "指定されたリソースが見つかりません。",
        "field_errors": [],
    }


def test_conflict_uses_unified_shape() -> None:
    application = create_app()

    @application.get("/api/v1/test/conflict")
    def conflict_route() -> None:
        raise ConflictError()

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "code": "CONFLICT",
        "message": "処理が競合しました。",
        "field_errors": [],
    }


def test_internal_error_hides_exception_details() -> None:
    application = create_app()
    sensitive_message = "database password leaked"

    @application.get("/api/v1/test/unexpected")
    def unexpected_route() -> None:
        raise RuntimeError(sensitive_message)

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test/unexpected")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "サーバー内部でエラーが発生しました。",
        "field_errors": [],
    }
    assert sensitive_message not in response.text
