export type FieldError = {
  field: string;
  code: string;
  message: string;
};

export type ApiErrorBody = {
  code: string;
  message: string;
  field_errors: FieldError[];
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldError[];

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.fieldErrors = body.field_errors;
  }
}
