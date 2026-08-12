import { apiFetch, apiUrl } from "./client";

export type CsvImportErrorItem = {
  row_number: number;
  field_name: string;
  error_code: string;
  error_message: string;
  input_value: string;
};

export type CsvImportJob = {
  id: number;
  import_type: "PRODUCT_MASTER";
  file_name: string;
  status: "PROCESSING" | "SUCCEEDED" | "FAILED";
  total_rows: number;
  success_rows: number;
  error_rows: number;
  accepted_at: string;
  completed_at: string | null;
  errors: CsvImportErrorItem[];
  error_csv_available: boolean;
};

export function uploadProductsCsv(file: File): Promise<CsvImportJob> {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<CsvImportJob>("/imports/products", { method: "POST", body });
}

export function productImportErrorCsvUrl(jobId: number): string {
  return apiUrl(`/imports/products/${jobId}/errors.csv`);
}
