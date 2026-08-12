import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import {
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

import { fetchHealth } from "./api/health";
import {
  createOrder,
  fetchMasters,
  fetchOrder,
  fetchOrders,
  transitionOrder,
  updateOrder,
  type OrderInput,
} from "./api/manufacturing";
import {
  EquipmentPage,
  ReceiptDetailPage,
  ProcessPanel,
  ReceiptFormPage,
  ReceiptListPage,
} from "./Phase3";
import {
  DashboardPanel,
  InventoryBalancePage,
  InventoryTransactionsPage,
  ReportsPage,
  ShipmentDetailPage,
  ShipmentFormPage,
  ShipmentListPage,
} from "./Phase4";
import { CsvImportPage } from "./CsvImportPage";
import { MasterManagementPage } from "./MasterManagement";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header>
        <strong>TEA-V1 お茶製造管理システム</strong>
        <nav>
          <Link to="/">ダッシュボード</Link>{" "}
          <Link to="/manufacturing-orders">製造指示</Link>{" "}
          <Link to="/manufacturing-orders/new">新規登録</Link>{" "}
          <Link to="/raw-material-receipts">原料入荷</Link>{" "}
          <Link to="/masters/tea-leaves">茶葉</Link>{" "}
          <Link to="/masters/varieties">品種</Link>{" "}
          <Link to="/masters/suppliers">仕入先</Link>{" "}
          <Link to="/masters/equipment">設備</Link>{" "}
          <Link to="/masters/products">製品</Link>{" "}
          <Link to="/inventory/raw-materials">原料在庫</Link>{" "}
          <Link to="/inventory/products">製品在庫</Link>{" "}
          <Link to="/inventory/transactions">在庫履歴</Link>{" "}
          <Link to="/shipments">出荷</Link> <Link to="/reports">集計</Link>{" "}
          <Link to="/imports/products">製品CSV取込</Link>
        </nav>
      </header>
      <main className="app-shell">{children}</main>
    </>
  );
}

function HealthPage() {
  const query = useQuery({
    queryKey: ["backend-health"],
    queryFn: fetchHealth,
    retry: false,
  });
  return (
    <Layout>
      <section className="status-card">
        <h1>お茶製造管理システム</h1>
        {query.isPending && <p role="status">backend health取得中</p>}
        {query.isSuccess && (
          <p role="status">backend health成功: {query.data.status}</p>
        )}
        {query.isError && <p role="alert">backend health失敗</p>}
      </section>
      <DashboardPanel />
    </Layout>
  );
}

function OrderListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const filters = {
    status: searchParams.get("status") ?? "",
    product_id: searchParams.get("product_id") ?? "",
    planned_date_from: searchParams.get("planned_date_from") ?? "",
    planned_date_to: searchParams.get("planned_date_to") ?? "",
  };
  const query = useQuery({
    queryKey: ["manufacturing-orders", page, filters],
    queryFn: () => fetchOrders(page, 20, filters),
  });
  return (
    <Layout>
      <h1>製造指示一覧</h1>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const next = new URLSearchParams({ page: "1", page_size: "20" });
          for (const key of [
            "status",
            "product_id",
            "planned_date_from",
            "planned_date_to",
          ]) {
            const value = String(data.get(key) ?? "");
            if (value) next.set(key, value);
          }
          setSearchParams(next);
        }}
      >
        <label>
          状態
          <select name="status" defaultValue={filters.status}>
            <option value="">すべて</option>
            {Object.keys(actions)
              .concat(["COMPLETED", "CANCELLED"])
              .map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
          </select>
        </label>
        <label>
          製品ID
          <input
            name="product_id"
            type="number"
            min="1"
            defaultValue={filters.product_id}
          />
        </label>
        <label>
          予定日（開始）
          <input
            name="planned_date_from"
            type="date"
            defaultValue={filters.planned_date_from}
          />
        </label>
        <label>
          予定日（終了）
          <input
            name="planned_date_to"
            type="date"
            defaultValue={filters.planned_date_to}
          />
        </label>
        <button>絞り込む</button>
      </form>
      {query.isPending && <p role="status">製造指示を取得中</p>}
      {query.isError && <p role="alert">製造指示の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>製造指示はありません</p>}
      {query.data?.items.map((order) => (
        <article key={order.id}>
          <Link to={`/manufacturing-orders/${order.id}`}>
            {order.order_number}
          </Link>{" "}
          {order.status} / {order.planned_quantity.toFixed(3)} kg
        </article>
      ))}
      {query.data && query.data.total_pages > 0 && (
        <nav aria-label="ページング">
          <button
            disabled={page <= 1}
            onClick={() =>
              setSearchParams((current) => {
                current.set("page", String(page - 1));
                current.set("page_size", "20");
                return current;
              })
            }
          >
            前へ
          </button>
          <span>
            {page} / {query.data.total_pages}
          </span>
          <button
            disabled={page >= query.data.total_pages}
            onClick={() =>
              setSearchParams((current) => {
                current.set("page", String(page + 1));
                current.set("page_size", "20");
                return current;
              })
            }
          >
            次へ
          </button>
        </nav>
      )}
    </Layout>
  );
}

function OrderFormPage() {
  const navigate = useNavigate();
  const { orderId } = useParams();
  const editingId = orderId ? Number(orderId) : null;
  const existing = useQuery({
    queryKey: ["manufacturing-order", orderId],
    queryFn: () => fetchOrder(orderId ?? ""),
    enabled: editingId !== null,
  });
  const products = useQuery({
    queryKey: ["masters", "products"],
    queryFn: () => fetchMasters("products"),
  });
  const equipment = useQuery({
    queryKey: ["masters", "equipment"],
    queryFn: () => fetchMasters("equipment"),
  });
  const teaLeaves = useQuery({
    queryKey: ["masters", "tea-leaves"],
    queryFn: () => fetchMasters("tea-leaves"),
  });
  const varieties = useQuery({
    queryKey: ["masters", "varieties"],
    queryFn: () => fetchMasters("varieties"),
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<OrderInput>({
    defaultValues: {
      materials: [{ tea_leaf_id: 0, variety_id: 0, planned_quantity: "0.001" }],
    },
  });
  useEffect(() => {
    if (!existing.data) return;
    reset({
      order_number: existing.data.order_number,
      product_id: existing.data.product_id,
      planned_quantity: existing.data.planned_quantity.toFixed(3),
      planned_date: existing.data.planned_date,
      equipment_id: existing.data.equipment_id,
      materials: existing.data.materials.map((item) => ({
        tea_leaf_id: item.tea_leaf_id,
        variety_id: item.variety_id,
        planned_quantity: item.planned_quantity.toFixed(3),
      })),
    });
  }, [existing.data, reset]);
  const mutation = useMutation({
    mutationFn: (value: OrderInput) =>
      editingId === null ? createOrder(value) : updateOrder(editingId, value),
    onSuccess: (order) => navigate(`/manufacturing-orders/${order.id}`),
  });
  const loading = [
    products,
    equipment,
    teaLeaves,
    varieties,
    ...(editingId ? [existing] : []),
  ].some((item) => item.isPending);
  const failed = [
    products,
    equipment,
    teaLeaves,
    varieties,
    ...(editingId ? [existing] : []),
  ].some((item) => item.isError);
  if (loading)
    return (
      <Layout>
        <p role="status">マスタを取得中</p>
      </Layout>
    );
  if (failed)
    return (
      <Layout>
        <p role="alert">マスタの取得に失敗しました</p>
      </Layout>
    );
  return (
    <Layout>
      <h1>{editingId === null ? "製造指示登録" : "製造指示編集"}</h1>
      {mutation.isError && (
        <p role="alert">
          {editingId === null ? "登録に失敗しました" : "保存に失敗しました"}
        </p>
      )}
      <form onSubmit={handleSubmit((value) => mutation.mutate(value))}>
        <label>
          製造指示番号
          <input {...register("order_number", { required: true })} />
        </label>
        {errors.order_number && <span>必須です</span>}
        <label>
          製品
          <select {...register("product_id", { valueAsNumber: true, min: 1 })}>
            <option value="0">選択</option>
            {products.data
              ?.filter((x) => x.is_active)
              .map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          予定数量 (kg)
          <input
            type="number"
            step="0.001"
            min="0.001"
            {...register("planned_quantity", { required: true, min: 0.001 })}
          />
        </label>
        <label>
          予定日
          <input
            type="date"
            {...register("planned_date", { required: true })}
          />
        </label>
        <label>
          設備
          <select
            {...register("equipment_id", { valueAsNumber: true, min: 1 })}
          >
            <option value="0">選択</option>
            {equipment.data
              ?.filter((x) => x.is_active)
              .map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          茶葉
          <select
            {...register("materials.0.tea_leaf_id", {
              valueAsNumber: true,
              min: 1,
            })}
          >
            <option value="0">選択</option>
            {teaLeaves.data
              ?.filter((x) => x.is_active)
              .map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          品種
          <select
            {...register("materials.0.variety_id", {
              valueAsNumber: true,
              min: 1,
            })}
          >
            <option value="0">選択</option>
            {varieties.data
              ?.filter((x) => x.is_active)
              .map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          原料予定使用量 (kg)
          <input
            type="number"
            step="0.001"
            min="0.001"
            {...register("materials.0.planned_quantity", {
              required: true,
              min: 0.001,
            })}
          />
        </label>
        <button disabled={mutation.isPending}>
          {mutation.isPending
            ? editingId === null
              ? "登録中"
              : "保存中"
            : editingId === null
              ? "下書き登録"
              : "下書き保存"}
        </button>
      </form>
    </Layout>
  );
}

const actions: Record<string, Array<{ key: string; label: string }>> = {
  DRAFT: [
    { key: "issue", label: "指示確定" },
    { key: "cancel", label: "取消" },
  ],
  ISSUED: [
    { key: "start", label: "製造開始" },
    { key: "cancel", label: "取消" },
  ],
  IN_PROGRESS: [{ key: "complete", label: "製造完了" }],
};
function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["manufacturing-order", orderId],
    queryFn: () => fetchOrder(orderId),
  });
  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) =>
      transitionOrder(id, action),
    onSuccess: (order) => {
      client.setQueryData(["manufacturing-order", orderId], order);
      client.invalidateQueries({ queryKey: ["manufacturing-orders"] });
    },
  });
  return (
    <Layout>
      <h1>製造指示詳細</h1>
      {query.isPending && <p role="status">製造指示を取得中</p>}
      {query.isError && <p role="alert">製造指示の取得に失敗しました</p>}
      {mutation.isError && <p role="alert">状態操作に失敗しました</p>}
      {query.data && (
        <section>
          <p>{query.data.order_number}</p>
          <p>状態: {query.data.status}</p>
          <p>製品: {query.data.product_name}</p>
          <p>設備: {query.data.equipment_name}</p>
          <p>予定数量: {query.data.planned_quantity.toFixed(3)} kg</p>
          <h2>使用原料</h2>
          {query.data.materials.map((material) => (
            <p key={material.id}>
              {material.tea_leaf_name} / {material.variety_name} /{" "}
              {material.planned_quantity.toFixed(3)} kg
            </p>
          ))}
          {query.data.status === "DRAFT" && (
            <Link to={`/manufacturing-orders/${query.data.id}/edit`}>
              下書き編集
            </Link>
          )}
          {(actions[query.data.status] ?? []).map((action) => (
            <button
              key={action.key}
              disabled={mutation.isPending}
              onClick={() =>
                mutation.mutate({ id: query.data.id, action: action.key })
              }
            >
              {action.label}
            </button>
          ))}
          {["COMPLETED", "CANCELLED"].includes(query.data.status) && (
            <p>完了・取消済みのため読み取り専用です。</p>
          )}
          <ProcessPanel
            orderId={query.data.id}
            orderStatus={query.data.status}
          />
          <section>
            <h2>関連在庫履歴</h2>
            {query.data.inventory_transactions.length === 0 && (
              <p>関連在庫履歴はありません</p>
            )}
            {query.data.inventory_transactions.map((item) => (
              <p key={item.id}>
                {item.transaction_type} / {item.quantity_delta.toFixed(3)} kg /
                残高 {item.balance_after.toFixed(3)} kg
              </p>
            ))}
          </section>
        </section>
      )}
    </Layout>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HealthPage />} />
      <Route path="/manufacturing-orders" element={<OrderListPage />} />
      <Route path="/manufacturing-orders/new" element={<OrderFormPage />} />
      <Route
        path="/manufacturing-orders/:orderId/edit"
        element={<OrderFormPage />}
      />
      <Route
        path="/manufacturing-orders/:orderId"
        element={<OrderDetailPage />}
      />
      <Route
        path="/raw-material-receipts"
        element={
          <Layout>
            <ReceiptListPage />
          </Layout>
        }
      />
      <Route
        path="/raw-material-receipts/new"
        element={
          <Layout>
            <ReceiptFormPage />
          </Layout>
        }
      />
      <Route
        path="/raw-material-receipts/:receiptId"
        element={
          <Layout>
            <ReceiptDetailPage />
          </Layout>
        }
      />
      <Route
        path="/equipment"
        element={
          <Layout>
            <EquipmentPage />
          </Layout>
        }
      />
      {(
        [
          "tea-leaves",
          "varieties",
          "suppliers",
          "equipment",
          "products",
        ] as const
      ).map((resource) => (
        <Route
          key={resource}
          path={`/masters/${resource}`}
          element={
            <Layout>
              <MasterManagementPage resource={resource} />
            </Layout>
          }
        />
      ))}
      <Route
        path="/inventory/raw-materials"
        element={
          <Layout>
            <InventoryBalancePage kind="raw" />
          </Layout>
        }
      />
      <Route
        path="/inventory/products"
        element={
          <Layout>
            <InventoryBalancePage kind="product" />
          </Layout>
        }
      />
      <Route
        path="/inventory/transactions"
        element={
          <Layout>
            <InventoryTransactionsPage />
          </Layout>
        }
      />
      <Route
        path="/shipments"
        element={
          <Layout>
            <ShipmentListPage />
          </Layout>
        }
      />
      <Route
        path="/shipments/new"
        element={
          <Layout>
            <ShipmentFormPage />
          </Layout>
        }
      />
      <Route
        path="/shipments/:shipmentId"
        element={
          <Layout>
            <ShipmentDetailPage />
          </Layout>
        }
      />
      <Route
        path="/reports"
        element={
          <Layout>
            <ReportsPage />
          </Layout>
        }
      />
      <Route
        path="/imports/products"
        element={
          <Layout>
            <CsvImportPage />
          </Layout>
        }
      />
      <Route
        path="*"
        element={
          <Layout>
            <h1>Not Found</h1>
          </Layout>
        }
      />
    </Routes>
  );
}
