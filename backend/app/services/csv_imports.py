import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models.manufacturing import (
    CsvImportError,
    CsvImportJob,
    CsvImportStatus,
    CsvImportType,
    Product,
    ProductInventoryBalance,
    Variety,
)
from app.schemas.csv_imports import CsvImportJobResponse

EXPECTED_HEADER = ["product_code", "product_name", "variety_code", "is_active"]
MAX_FILE_SIZE = 1024 * 1024
MAX_DATA_ROWS = 1000
PRODUCT_CODE_MAX_LENGTH = 30
PRODUCT_NAME_MAX_LENGTH = 100


@dataclass(frozen=True)
class ParsedProductRow:
    row_number: int
    product_code: str
    product_name: str
    variety_code: str
    is_active: bool


@dataclass(frozen=True)
class ImportErrorData:
    row_number: int
    field_name: str
    error_code: str
    error_message: str
    input_value: str


def _error(
    row_number: int,
    field_name: str,
    error_code: str,
    error_message: str,
    input_value: str = "",
) -> ImportErrorData:
    return ImportErrorData(
        row_number=row_number,
        field_name=field_name,
        error_code=error_code,
        error_message=error_message,
        input_value=input_value,
    )


def _read_records(text: str) -> list[tuple[int, list[str]]]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    records: list[tuple[int, list[str]]] = []
    while True:
        start_line = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            return records
        records.append((start_line, row))


def _validate_file(filename: str, content: bytes) -> list[ImportErrorData]:
    errors = []
    if not filename or not filename.endswith(".csv"):
        errors.append(
            _error(
                0,
                "file",
                "INVALID_FILE_TYPE",
                "拡張子が.csvのファイルを選択してください。",
                filename,
            )
        )
    if len(content) > MAX_FILE_SIZE:
        errors.append(
            _error(
                0,
                "file",
                "FILE_TOO_LARGE",
                "ファイルサイズは1 MiB以下にしてください。",
                str(len(content)),
            )
        )
    return errors


def parse_and_validate(
    session: Session, filename: str, content: bytes
) -> tuple[list[ParsedProductRow], int, list[ImportErrorData], dict[str, Variety]]:
    errors = _validate_file(filename, content)
    if errors:
        return [], 0, errors, {}
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return (
            [],
            0,
            [_error(0, "file", "INVALID_ENCODING", "UTF-8形式のCSVを選択してください。")],
            {},
        )
    try:
        records = _read_records(text)
    except csv.Error:
        return [], 0, [_error(0, "file", "INVALID_FORMAT", "CSV形式を解析できませんでした。")], {}
    if not records or records[0][1] != EXPECTED_HEADER:
        actual = ",".join(records[0][1]) if records else ""
        return (
            [],
            0,
            [
                _error(
                    0,
                    "header",
                    "INVALID_HEADER",
                    "ヘッダー名と順序を確認してください。",
                    actual,
                )
            ],
            {},
        )

    data_records = records[1:]
    while data_records and data_records[-1][1] == []:
        data_records.pop()
    total_rows = len(data_records)
    if total_rows == 0:
        return [], 0, [_error(0, "", "EMPTY_FILE", "データ行がありません。")], {}
    if total_rows > MAX_DATA_ROWS:
        return (
            [],
            total_rows,
            [
                _error(
                    0,
                    "file",
                    "TOO_MANY_ROWS",
                    "データ行数は1,000行以下にしてください。",
                    str(total_rows),
                )
            ],
            {},
        )

    candidates: list[tuple[int, dict[str, str]]] = []
    for row_number, values in data_records:
        if values == []:
            errors.append(_error(row_number, "", "EMPTY_ROW", "データ途中の空行は使用できません。"))
            continue
        if len(values) != len(EXPECTED_HEADER):
            errors.append(
                _error(
                    row_number,
                    "",
                    "INVALID_FORMAT",
                    "列数がヘッダーと一致しません。",
                    ",".join(values),
                )
            )
            continue
        values_by_field = dict(zip(EXPECTED_HEADER, values, strict=True))
        candidates.append((row_number, values_by_field))
        for field_name, value in values_by_field.items():
            if not value.strip():
                errors.append(_error(row_number, field_name, "REQUIRED", "必須項目です。", value))
        if len(values_by_field["product_code"]) > PRODUCT_CODE_MAX_LENGTH:
            errors.append(
                _error(
                    row_number,
                    "product_code",
                    "MAX_LENGTH",
                    "製品コードは30文字以下にしてください。",
                    values_by_field["product_code"],
                )
            )
        if len(values_by_field["product_name"]) > PRODUCT_NAME_MAX_LENGTH:
            errors.append(
                _error(
                    row_number,
                    "product_name",
                    "MAX_LENGTH",
                    "製品名は100文字以下にしてください。",
                    values_by_field["product_name"],
                )
            )
        if values_by_field["is_active"] not in {"true", "false"}:
            errors.append(
                _error(
                    row_number,
                    "is_active",
                    "INVALID_FORMAT",
                    "trueまたはfalseを指定してください。",
                    values_by_field["is_active"],
                )
            )

    code_rows: dict[str, list[int]] = defaultdict(list)
    for row_number, values in candidates:
        if values["product_code"]:
            code_rows[values["product_code"]].append(row_number)
    for code, row_numbers in code_rows.items():
        if len(row_numbers) > 1:
            errors.extend(
                _error(
                    row_number,
                    "product_code",
                    "DUPLICATE_IN_FILE",
                    "CSV内で製品コードが重複しています。",
                    code,
                )
                for row_number in row_numbers
            )

    product_codes = list(code_rows)
    existing_codes = set(
        session.scalars(select(Product.code).where(Product.code.in_(product_codes))).all()
    )
    for row_number, values in candidates:
        if values["product_code"] in existing_codes:
            errors.append(
                _error(
                    row_number,
                    "product_code",
                    "DUPLICATE_IN_DATABASE",
                    "製品コードは既に登録されています。",
                    values["product_code"],
                )
            )

    variety_codes = {values["variety_code"] for _, values in candidates if values["variety_code"]}
    varieties = {
        variety.code: variety
        for variety in session.scalars(select(Variety).where(Variety.code.in_(variety_codes)))
    }
    for row_number, values in candidates:
        code = values["variety_code"]
        if not code:
            continue
        variety = varieties.get(code)
        if variety is None:
            errors.append(
                _error(
                    row_number,
                    "variety_code",
                    "REFERENCE_NOT_FOUND",
                    "品種コードが見つかりません。",
                    code,
                )
            )
        elif not variety.is_active:
            errors.append(
                _error(
                    row_number,
                    "variety_code",
                    "REFERENCE_INACTIVE",
                    "無効な品種は使用できません。",
                    code,
                )
            )

    parsed_rows = [
        ParsedProductRow(
            row_number=row_number,
            product_code=values["product_code"],
            product_name=values["product_name"],
            variety_code=values["variety_code"],
            is_active=values["is_active"] == "true",
        )
        for row_number, values in candidates
    ]
    return parsed_rows, total_rows, errors, varieties


def _create_job(session: Session, filename: str) -> CsvImportJob:
    job = CsvImportJob(
        import_type=CsvImportType.PRODUCT_MASTER,
        file_name=filename,
        status=CsvImportStatus.PROCESSING,
        total_rows=0,
        success_rows=0,
        error_rows=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _finish_failed_job(
    session: Session,
    job_id: int,
    total_rows: int,
    errors: list[ImportErrorData],
) -> CsvImportJob:
    job = session.get(CsvImportJob, job_id)
    if job is None:
        raise RuntimeError("CSV import job disappeared")
    job.status = CsvImportStatus.FAILED
    job.total_rows = total_rows
    job.success_rows = 0
    job.error_rows = len({error.row_number for error in errors})
    job.completed_at = datetime.now(UTC)
    job.errors = [CsvImportError(**error.__dict__) for error in errors]
    session.commit()
    return get_import_job(session, job.id)


def _save_products(
    session: Session,
    job: CsvImportJob,
    rows: list[ParsedProductRow],
    varieties: dict[str, Variety],
) -> None:
    products = [
        Product(
            code=row.product_code,
            name=row.product_name,
            variety_id=varieties[row.variety_code].id,
            is_active=row.is_active,
        )
        for row in rows
    ]
    session.add_all(products)
    session.flush()
    session.add_all(
        [
            ProductInventoryBalance(product_id=product.id, quantity=Decimal("0.000"))
            for product in products
        ]
    )
    session.flush()
    job.status = CsvImportStatus.SUCCEEDED
    job.total_rows = len(rows)
    job.success_rows = len(rows)
    job.error_rows = 0
    job.completed_at = datetime.now(UTC)
    session.commit()


def import_products(session: Session, filename: str, content: bytes) -> CsvImportJob:
    job = _create_job(session, filename)
    rows, total_rows, errors, varieties = parse_and_validate(session, filename, content)
    if errors:
        return _finish_failed_job(session, job.id, total_rows, errors)
    try:
        _save_products(session, job, rows, varieties)
    except Exception as exc:
        session.rollback()
        database_error = _error(
            0,
            "",
            "DATABASE_ERROR",
            "データベース登録中にエラーが発生しました。",
        )
        _finish_failed_job(session, job.id, total_rows, [database_error])
        raise RuntimeError("CSV import database operation failed") from exc
    return get_import_job(session, job.id)


def get_import_job(session: Session, job_id: int) -> CsvImportJob:
    job = session.scalar(
        select(CsvImportJob)
        .options(selectinload(CsvImportJob.errors))
        .where(CsvImportJob.id == job_id)
    )
    if job is None:
        raise NotFoundError("CSV取込結果が見つかりません。")
    return job


def import_job_response(job: CsvImportJob) -> CsvImportJobResponse:
    return CsvImportJobResponse.model_validate(
        {**job.__dict__, "error_csv_available": bool(job.errors)}
    )


def build_error_csv(job: CsvImportJob) -> bytes:
    if not job.errors:
        raise NotFoundError("この取込結果にエラーCSVはありません。")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(["row_number", "field_name", "error_code", "error_message", "input_value"])
    for error in job.errors:
        writer.writerow(
            [
                error.row_number,
                error.field_name,
                error.error_code,
                error.error_message,
                error.input_value,
            ]
        )
    return output.getvalue().encode("utf-8")
