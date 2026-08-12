import { apiFetch } from "./client";

export type ManufacturingStatus =
  "DRAFT" | "ISSUED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type Master = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
  variety_id?: number;
};
export type ManufacturingOrder = {
  id: number;
  order_number: string;
  product_id: number;
  product_name: string;
  planned_quantity: number;
  planned_date: string;
  equipment_id: number;
  equipment_name: string;
  status: ManufacturingStatus;
  started_at: string | null;
  completed_at: string | null;
  materials: Array<{
    id: number;
    tea_leaf_id: number;
    variety_id: number;
    planned_quantity: number;
    tea_leaf_name: string;
    variety_name: string;
  }>;
  processes: Array<{
    id: number;
    sequence: number;
    process_code: string;
    process_name: string;
    status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
    equipment_id: number | null;
    equipment_name: string | null;
    started_at: string | null;
    completed_at: string | null;
    result_note: string | null;
  }>;
  inventory_transactions: Array<{
    id: number;
    inventory_kind: "RAW_MATERIAL" | "PRODUCT";
    transaction_type: string;
    quantity_delta: number;
    balance_after: number;
    occurred_at: string;
  }>;
};
export type OrderList = {
  items: ManufacturingOrder[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};
export type OrderInput = {
  order_number: string;
  product_id: number;
  planned_quantity: string;
  planned_date: string;
  equipment_id: number;
  materials: Array<{
    tea_leaf_id: number;
    variety_id: number;
    planned_quantity: string;
  }>;
};

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export type OrderFilters = {
  status?: string;
  product_id?: string;
  planned_date_from?: string;
  planned_date_to?: string;
};
export const fetchOrders = (
  page = 1,
  pageSize = 20,
  filters: OrderFilters = {},
) => {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  return apiFetch<OrderList>(`/manufacturing-orders?${params.toString()}`);
};
export const fetchOrder = (id: string) =>
  apiFetch<ManufacturingOrder>(`/manufacturing-orders/${id}`);
export const createOrder = (body: OrderInput) =>
  apiFetch<ManufacturingOrder>("/manufacturing-orders", json(body));
export const updateOrder = (id: number, body: OrderInput) =>
  apiFetch<ManufacturingOrder>(`/manufacturing-orders/${id}`, {
    ...json(body),
    method: "PUT",
  });
export const transitionOrder = (id: number, action: string) =>
  apiFetch<ManufacturingOrder>(`/manufacturing-orders/${id}/${action}`, {
    method: "POST",
  });
export type MasterPage = {
  items: Master[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};
export type MasterResource =
  "tea-leaves" | "varieties" | "equipment" | "products" | "suppliers";
export const fetchMasterPage = (
  resource: MasterResource,
  page = 1,
  pageSize = 20,
) =>
  apiFetch<MasterPage>(
    `/masters/${resource}?page=${page}&page_size=${pageSize}`,
  );
export const fetchMasters = async (
  resource: "tea-leaves" | "varieties" | "equipment" | "products" | "suppliers",
) => (await fetchMasterPage(resource, 1, 100)).items;
export type MasterInput = Pick<Master, "code" | "name" | "is_active"> & {
  variety_id?: number;
};
export const createMaster = (resource: MasterResource, body: MasterInput) =>
  apiFetch<Master>(`/masters/${resource}`, json(body));
export const updateMaster = (
  resource: MasterResource,
  id: number,
  body: MasterInput,
) =>
  apiFetch<Master>(`/masters/${resource}/${id}`, {
    ...json(body),
    method: "PUT",
  });
