import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings


def create_database_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def ensure_test_database_url(database_url: str) -> URL:
    try:
        parsed_url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError("TEST_DATABASE_URL is not a valid database URL.") from exc
    database_name = parsed_url.database or ""
    if not database_name.endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must reference a database ending in '_test'.")
    return parsed_url


def ensure_matching_test_database_urls(database_url: str, test_database_url: str) -> URL:
    parsed_database_url = ensure_test_database_url(database_url)
    parsed_test_database_url = ensure_test_database_url(test_database_url)
    if parsed_database_url != parsed_test_database_url:
        message = "DATABASE_URL and TEST_DATABASE_URL must reference the same test database."
        raise RuntimeError(message)
    return parsed_database_url


@lru_cache
def get_database_engine() -> Engine:
    return create_database_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_database_engine(), class_=Session, expire_on_commit=False)


def reset_database_state() -> None:
    if get_database_engine.cache_info().currsize:
        get_database_engine().dispose()
    get_session_factory.cache_clear()
    get_database_engine.cache_clear()


def activate_test_database(test_database_url: str) -> URL:
    parsed_url = ensure_test_database_url(test_database_url)
    reset_database_state()
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    return parsed_url


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
