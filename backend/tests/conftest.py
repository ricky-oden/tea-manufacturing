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

from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
