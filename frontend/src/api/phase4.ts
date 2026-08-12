import { apiFetch } from "./client";

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type RawBalance = {
  id: number;
  tea_leaf_id: number;
  tea_leaf_code: string;
  tea_leaf_name: string;
  variety_id: number;
  variety_code: string;
  variety_name: string;
  quantity: number;
  unit: "kg";
  updated_at: string;
};

export type ProductBalance = {
  id: number;
  product_id: number;
  product_code: string;
  product_name: string;
  quantity: number;
  unit: "kg";
  updated_at: string;
};

export type InventoryTransaction = {
  id: number;
  inventory_kind: "RAW_MATERIAL" | "PRODUCT";
  transaction_type:
    | "RECEIPT"
    | "MANUFACTURING_CONSUMPTION"
    | "MANUFACTURING_OUTPUT"
    | "SHIPMENT";
  target_code: string;
  target_name: string;
  quantity_delta: number;
  balance_after: number;
  unit: "kg";
  occurred_at: string;
};

export type ShipmentInput = {
  shipment_number: string;
  shipped_date: string;
  lines: Array<{ product_id: number; quantity: string }>;
};

export type Shipment = {
  id: number;
  shipment_number: string;
  shipped_date: string;
  status: "DRAFT" | "CONFIRMED";
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  lines: Array<{
    id: number;
    product_id: number;
    product_code: string;
    product_name: string;
    quantity: number;
  }>;
};

export type Breakdown = { code: string; name: string; quantity: number };
export type Summary = {
  date_from: string;
  date_to: string;
  receipt_quantity: number;
  manufacturing_quantity: number;
  shipment_quantity: number;
  current_raw_material_quantity: number;
  current_product_quantity: number;
  receipt_breakdown: Breakdown[];
  manufacturing_breakdown: Breakdown[];
  shipment_breakdown: Breakdown[];
};
export type Dashboard = {
  date_from: string;
  date_to: string;
  manufacturing_status_counts: Record<string, number>;
  raw_material_inventory: {
    item_count: number;
    total_quantity: number;
    unit: "kg";
  };
  product_inventory: { item_count: number; total_quantity: number; unit: "kg" };
  receipt_quantity: number;
  manufacturing_quantity: number;
  shipment_quantity: number;
};

const json = (method: "POST" | "PUT", body?: unknown): RequestInit => ({
  method,
  headers:
    body === undefined ? undefined : { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const fetchRawBalances = (page = 1, pageSize = 20) =>
  apiFetch<Page<RawBalance>>(
    `/inventories/raw-materials?page=${page}&page_size=${pageSize}`,
  );
export const fetchProductBalances = (page = 1, pageSize = 20) =>
  apiFetch<Page<ProductBalance>>(
    `/inventories/products?page=${page}&page_size=${pageSize}`,
  );
export const fetchInventoryTransactions = (query: string) =>
  apiFetch<Page<InventoryTransaction>>(`/inventory-transactions?${query}`);
export const fetchShipments = (page = 1, pageSize = 20) =>
  apiFetch<Page<Shipment>>(`/shipments?page=${page}&page_size=${pageSize}`);
export const fetchShipment = (id: string) =>
  apiFetch<Shipment>(`/shipments/${id}`);
export const createShipment = (body: ShipmentInput) =>
  apiFetch<Shipment>("/shipments", json("POST", body));
export const updateShipment = (id: number, body: ShipmentInput) =>
  apiFetch<Shipment>(`/shipments/${id}`, json("PUT", body));
export const confirmShipment = (id: number) =>
  apiFetch<Shipment>(`/shipments/${id}/confirm`, json("POST"));
export const fetchSummary = (dateFrom: string, dateTo: string) =>
  apiFetch<Summary>(`/reports/summary?date_from=${dateFrom}&date_to=${dateTo}`);
export const fetchDashboard = (dateFrom: string, dateTo: string) =>
  apiFetch<Dashboard>(`/dashboard?date_from=${dateFrom}&date_to=${dateTo}`);

export function tokyoToday(): string {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function defaultPeriod(): { dateFrom: string; dateTo: string } {
  const dateTo = tokyoToday();
  const start = new Date(`${dateTo}T00:00:00+09:00`);
  start.setUTCDate(start.getUTCDate() - 29);
  const dateFrom = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(start);
  return { dateFrom, dateTo };
}
