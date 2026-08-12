from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TEA-V1 お茶製造管理システム"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "postgresql+psycopg://tea_app:tea_local_password@db:5432/tea_manufacturing"
    test_database_url: str = (
        "postgresql+psycopg://tea_test:tea_test_password@test-db:5432/tea_manufacturing_test"
    )
    cors_allowed_origins: str = "http://localhost:5174"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
