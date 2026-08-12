import { apiFetch } from "./client";

export type HealthResponse = {
  status: "ok";
};

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
