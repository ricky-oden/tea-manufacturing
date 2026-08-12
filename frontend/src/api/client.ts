import { ApiError, type ApiErrorBody } from "./types";

const defaultApiBaseUrl = "/api/v1";
declare const __API_BASE_URL__: string | undefined;

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Partial<ApiErrorBody>;
  return (
    typeof candidate.code === "string" &&
    typeof candidate.message === "string" &&
    Array.isArray(candidate.field_errors)
  );
}

function currentApiBaseUrl(): string {
  return typeof __API_BASE_URL__ === "string"
    ? __API_BASE_URL__
    : defaultApiBaseUrl;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (response.ok) {
    return (await response.json()) as T;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }

  if (isApiErrorBody(body)) {
    throw new ApiError(response.status, body);
  }

  throw new ApiError(response.status, {
    code: "UNEXPECTED_API_ERROR",
    message: "APIから予期しない応答を受信しました。",
    field_errors: [],
  });
}

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${currentApiBaseUrl()}${normalizedPath}`;
}
