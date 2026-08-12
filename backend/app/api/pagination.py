from math import ceil
from typing import Any

PAGE_SIZE_MAX = 100


def page_response(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": ceil(total / page_size),
    }
