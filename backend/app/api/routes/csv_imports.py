from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.errors import PayloadTooLargeError
from app.db.session import get_db
from app.schemas.csv_imports import CsvImportJobResponse
from app.services.csv_imports import (
    MAX_FILE_SIZE,
    build_error_csv,
    get_import_job,
    import_job_response,
    import_products,
)

router = APIRouter(prefix="/imports/products", tags=["product-csv-imports"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CsvImportJobResponse)
async def upload_products_csv(
    session: DbSession, file: Annotated[UploadFile, File()]
) -> CsvImportJobResponse:
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise PayloadTooLargeError()
    job = import_products(session, file.filename or "", content)
    return import_job_response(job)


@router.get("/{job_id}", response_model=CsvImportJobResponse)
def import_detail(job_id: int, session: DbSession) -> CsvImportJobResponse:
    return import_job_response(get_import_job(session, job_id))


@router.get("/{job_id}/errors.csv")
def download_errors(job_id: int, session: DbSession) -> Response:
    content = build_error_csv(get_import_job(session, job_id))
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="product-import-errors-{job_id}.csv"'
        },
    )
