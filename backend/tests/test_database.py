import os
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import (
    activate_test_database,
    create_database_engine,
    ensure_matching_test_database_urls,
    ensure_test_database_url,
    get_database_engine,
    get_db,
)
from app.main import create_app


def test_test_database_guard_accepts_test_database() -> None:
    parsed_url = ensure_test_database_url(
        "postgresql+psycopg://tea_test:password@test-db:5432/tea_manufacturing_test"
    )

    assert parsed_url.database == "tea_manufacturing_test"


def test_test_database_guard_rejects_development_database() -> None:
    with pytest.raises(RuntimeError, match="ending in '_test'"):
        ensure_test_database_url("postgresql+psycopg://tea_app:password@db:5432/tea_manufacturing")


def test_test_database_guard_rejects_invalid_url() -> None:
    with pytest.raises(RuntimeError, match="not a valid database URL"):
        ensure_test_database_url("not-a-database-url")


def test_unsafe_test_database_does_not_replace_application_url() -> None:
    current_database_url = os.environ["DATABASE_URL"]

    with pytest.raises(RuntimeError, match="ending in '_test'"):
        activate_test_database("postgresql+psycopg://tea_app:password@db:5432/tea_manufacturing")

    assert os.environ["DATABASE_URL"] == current_database_url


def test_migration_guard_rejects_development_database_before_connection() -> None:
    with pytest.raises(RuntimeError, match="ending in '_test'"):
        ensure_matching_test_database_urls(
            "postgresql+psycopg://tea_app:password@db:5432/tea_manufacturing",
            "postgresql+psycopg://tea_test:password@test-db:5432/tea_manufacturing_test",
        )


def test_migration_guard_rejects_different_test_databases() -> None:
    with pytest.raises(RuntimeError, match="same test database"):
        ensure_matching_test_database_urls(
            "postgresql+psycopg://tea_test:password@test-db:5432/first_test",
            "postgresql+psycopg://tea_test:password@test-db:5432/second_test",
        )


def test_database_connection_smoke() -> None:
    settings = get_settings()
    ensure_test_database_url(settings.database_url)
    test_engine = create_database_engine(settings.database_url)

    try:
        with test_engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert (
                connection.execute(
                    text("SELECT current_database()"),
                )
                .scalar_one()
                .endswith("_test")
            )
    finally:
        test_engine.dispose()


def test_application_get_db_uses_test_database() -> None:
    settings = get_settings()
    engine_url = get_database_engine().url
    assert engine_url.database == "tea_manufacturing_test"
    assert engine_url.host == "test-db"
    assert engine_url.port == 5432
    assert settings.database_url == settings.test_database_url

    application: FastAPI = create_app()

    @application.get("/api/v1/test/database")
    def database_route(session: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
        database_name = session.execute(text("SELECT current_database()"))
        return {"database": database_name.scalar_one()}

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test/database")

    assert response.status_code == 200
    assert response.json() == {"database": "tea_manufacturing_test"}
