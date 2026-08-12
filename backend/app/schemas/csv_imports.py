from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.manufacturing import CsvImportStatus, CsvImportType


class CsvImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    field_name: str
    error_code: str
    error_message: str
    input_value: str


class CsvImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_type: CsvImportType
    file_name: str
    status: CsvImportStatus
    total_rows: int
    success_rows: int
    error_rows: int
    accepted_at: datetime
    completed_at: datetime | None
    errors: list[CsvImportErrorResponse]
    error_csv_available: bool
