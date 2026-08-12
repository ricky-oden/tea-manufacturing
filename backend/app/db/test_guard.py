from app.core.settings import get_settings
from app.db.session import ensure_matching_test_database_urls


def main() -> None:
    settings = get_settings()
    ensure_matching_test_database_urls(settings.database_url, settings.test_database_url)


if __name__ == "__main__":
    main()
