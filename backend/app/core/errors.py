import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    field_errors: list[FieldError] = Field(default_factory=list)


class AppError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ConflictError(AppError):
    def __init__(self, message: str = "処理が競合しました。") -> None:
        super().__init__(status_code=409, code="CONFLICT", message=message)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    field_errors: list[FieldError] | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        code=code,
        message=message,
        field_errors=field_errors or [],
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def install_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors = [
            FieldError(
                field=".".join(str(part) for part in error["loc"]),
                code=str(error["type"]),
                message=str(error["msg"]),
            )
            for error in exc.errors()
        ]
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="入力内容を確認してください。",
            field_errors=field_errors,
        )

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(
                status_code=404,
                code="NOT_FOUND",
                message="指定されたリソースが見つかりません。",
            )
        if exc.status_code == 409:
            return error_response(
                status_code=409,
                code="CONFLICT",
                message="処理が競合しました。",
            )
        return error_response(
            status_code=exc.status_code,
            code="HTTP_ERROR",
            message="リクエストを処理できませんでした。",
        )

    @application.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error while handling %s", request.url.path, exc_info=exc)
        return error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="サーバー内部でエラーが発生しました。",
        )


def error_response_schema() -> dict[str, Any]:
    return ApiErrorResponse.model_json_schema()
