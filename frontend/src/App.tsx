import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  type OrderInput,
} from "./api/manufacturing";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header>
        <strong>TEA-V1 お茶製造管理システム</strong>
        <nav>
          <Link to="/">基盤</Link>{" "}
          <Link to="/manufacturing-orders">製造指示</Link>{" "}
          <Link to="/manufacturing-orders/new">新規登録</Link>
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
    </Layout>
  );
}

function OrderListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const query = useQuery({
    queryKey: ["manufacturing-orders", page],
    queryFn: () => fetchOrders(page, 20),
  });
  return (
    <Layout>
      <h1>製造指示一覧</h1>
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
              setSearchParams({ page: String(page - 1), page_size: "20" })
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
              setSearchParams({ page: String(page + 1), page_size: "20" })
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
  } = useForm<OrderInput>({
    defaultValues: {
      materials: [{ tea_leaf_id: 0, variety_id: 0, planned_quantity: "0.001" }],
    },
  });
  const mutation = useMutation({
    mutationFn: createOrder,
    onSuccess: (order) => navigate(`/manufacturing-orders/${order.id}`),
  });
  const loading = [products, equipment, teaLeaves, varieties].some(
    (item) => item.isPending,
  );
  const failed = [products, equipment, teaLeaves, varieties].some(
    (item) => item.isError,
  );
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
      <h1>製造指示登録</h1>
      {mutation.isError && <p role="alert">登録に失敗しました</p>}
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
          {mutation.isPending ? "登録中" : "下書き登録"}
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
          <p>予定数量: {query.data.planned_quantity.toFixed(3)} kg</p>
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
        path="/manufacturing-orders/:orderId"
        element={<OrderDetailPage />}
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
