import { apiFetch } from "./client";

export type ManufacturingStatus =
  "DRAFT" | "ISSUED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
export type Master = {
  id: number;
  code: string;
  name: string;
  is_active: boolean;
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
export const fetchOrders = (page = 1, pageSize = 20) =>
  apiFetch<OrderList>(
    `/manufacturing-orders?page=${page}&page_size=${pageSize}`,
  );
export const fetchOrder = (id: string) =>
  apiFetch<ManufacturingOrder>(`/manufacturing-orders/${id}`);
export const createOrder = (body: OrderInput) =>
  apiFetch<ManufacturingOrder>("/manufacturing-orders", json(body));
export const transitionOrder = (id: number, action: string) =>
  apiFetch<ManufacturingOrder>(`/manufacturing-orders/${id}/${action}`, {
    method: "POST",
  });
export const fetchMasters = (
  resource: "tea-leaves" | "varieties" | "equipment" | "products" | "suppliers",
) => apiFetch<Master[]>(`/masters/${resource}`);
