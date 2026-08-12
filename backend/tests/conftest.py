import os

import pytest

from app.db.session import activate_test_database

try:
    activate_test_database(os.environ["TEST_DATABASE_URL"])
except KeyError as exc:
    raise pytest.UsageError("TEST_DATABASE_URL must be set before pytest starts.") from exc
except RuntimeError as exc:
    raise pytest.UsageError(str(exc)) from exc

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_database_engine, get_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import manufacturing  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> None:
    Base.metadata.create_all(get_database_engine())


@pytest.fixture(autouse=True)
def clean_business_tables(database_schema: None) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with get_database_engine().begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session() -> Session:
    with get_session_factory()() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
