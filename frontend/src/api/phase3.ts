import { apiFetch } from "./client";
import {
  fetchMasters,
  type Master,
  type ManufacturingStatus,
} from "./manufacturing";

export type ReceiptInput = {
  receipt_number: string;
  received_date: string;
  supplier_id: number;
  lines: Array<{
    tea_leaf_id: number;
    variety_id: number;
    quantity: string;
  }>;
};

export type Receipt = {
  id: number;
  receipt_number: string;
  received_date: string;
  supplier_id: number;
  supplier_name: string;
  created_at: string;
  lines: Array<{
    id: number;
    tea_leaf_id: number;
    tea_leaf_name: string;
    variety_id: number;
    variety_name: string;
    quantity: number;
  }>;
};

export type ReceiptList = {
  items: Receipt[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type ManufacturingProcess = {
  id: number;
  manufacturing_order_id: number;
  sequence: number;
  process_code: string;
  process_name: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
  equipment_id: number | null;
  equipment_name: string | null;
  started_at: string | null;
  completed_at: string | null;
  result_note: string | null;
};

export type EquipmentInput = Pick<Master, "code" | "name" | "is_active">;

const postJson = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const fetchReceipts = (page = 1, pageSize = 20) =>
  apiFetch<ReceiptList>(
    `/raw-material-receipts?page=${page}&page_size=${pageSize}`,
  );
export const createReceipt = (body: ReceiptInput) =>
  apiFetch<Receipt>("/raw-material-receipts", postJson(body));
export const fetchReceipt = (id: string) =>
  apiFetch<Receipt>(`/raw-material-receipts/${id}`);
export const fetchProcesses = (orderId: number) =>
  apiFetch<ManufacturingProcess[]>(
    `/manufacturing-orders/${orderId}/processes`,
  );
export const updateProcess = (
  orderId: number,
  processId: number,
  action: "start" | "complete",
) =>
  apiFetch<ManufacturingProcess>(
    `/manufacturing-orders/${orderId}/processes/${processId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    },
  );
export const fetchEquipment = () => fetchMasters("equipment");
export const createEquipment = (body: EquipmentInput) =>
  apiFetch<Master>("/masters/equipment", postJson(body));
export const updateEquipment = (id: number, body: EquipmentInput) =>
  apiFetch<Master>(`/masters/equipment/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const processActionsFor = (
  orderStatus: ManufacturingStatus,
  process: ManufacturingProcess,
) => {
  if (orderStatus !== "IN_PROGRESS") return [];
  if (process.status === "PENDING") return ["start"] as const;
  if (process.status === "IN_PROGRESS") return ["complete"] as const;
  return [];
};
