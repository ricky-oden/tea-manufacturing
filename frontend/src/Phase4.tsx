import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

import { fetchMasters } from "./api/manufacturing";
import {
  confirmShipment,
  createShipment,
  defaultPeriod,
  fetchDashboard,
  fetchInventoryTransactions,
  fetchProductBalances,
  fetchRawBalances,
  fetchShipment,
  fetchShipments,
  fetchSummary,
  updateShipment,
  type Page,
  type ProductBalance,
  type RawBalance,
  type Shipment,
  type ShipmentInput,
} from "./api/phase4";

function Pagination({
  page,
  totalPages,
}: {
  page: number;
  totalPages: number;
}) {
  const [params, setParams] = useSearchParams();
  const move = (target: number) => {
    const next = new URLSearchParams(params);
    next.set("page", String(target));
    next.set("page_size", "20");
    setParams(next);
  };
  if (totalPages === 0) return null;
  return (
    <nav aria-label="ページング">
      <button disabled={page <= 1} onClick={() => move(page - 1)}>
        前へ
      </button>
      <span>
        {page} / {totalPages}
      </span>
      <button disabled={page >= totalPages} onClick={() => move(page + 1)}>
        次へ
      </button>
    </nav>
  );
}

export function InventoryBalancePage({ kind }: { kind: "raw" | "product" }) {
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const query = useQuery<Page<RawBalance | ProductBalance>>({
    queryKey: ["inventory-balances", kind, page],
    queryFn: async () =>
      kind === "raw"
        ? await fetchRawBalances(page, 20)
        : await fetchProductBalances(page, 20),
  });
  const title = kind === "raw" ? "原料在庫" : "製品在庫";
  return (
    <section>
      <h1>{title}</h1>
      {query.isPending && <p role="status">{title}を取得中</p>}
      {query.isError && <p role="alert">{title}の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>{title}はありません</p>}
      {query.data?.items.map((item) => (
        <article key={item.id}>
          {"tea_leaf_code" in item
            ? `${item.tea_leaf_code} ${item.tea_leaf_name} / ${item.variety_code} ${item.variety_name}`
            : `${item.product_code} ${item.product_name}`}
          : {item.quantity.toFixed(3)} {item.unit}
        </article>
      ))}
      {query.data && (
        <Pagination page={page} totalPages={query.data.total_pages} />
      )}
    </section>
  );
}

type TransactionFilters = {
  inventory_kind: string;
  transaction_type: string;
  tea_leaf_id: string;
  variety_id: string;
  product_id: string;
  date_from: string;
  date_to: string;
};

export function InventoryTransactionsPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const { register, handleSubmit } = useForm<TransactionFilters>({
    defaultValues: {
      inventory_kind: params.get("inventory_kind") ?? "",
      transaction_type: params.get("transaction_type") ?? "",
      tea_leaf_id: params.get("tea_leaf_id") ?? "",
      variety_id: params.get("variety_id") ?? "",
      product_id: params.get("product_id") ?? "",
      date_from: params.get("date_from") ?? "",
      date_to: params.get("date_to") ?? "",
    },
  });
  const queryString = params.toString() || "page=1&page_size=20";
  const query = useQuery({
    queryKey: ["inventory-transactions", queryString],
    queryFn: () => fetchInventoryTransactions(queryString),
  });
  const search = (values: TransactionFilters) => {
    const next = new URLSearchParams({ page: "1", page_size: "20" });
    Object.entries(values).forEach(
      ([key, value]) => value && next.set(key, value),
    );
    setParams(next);
  };
  return (
    <section>
      <h1>在庫増減履歴</h1>
      <form onSubmit={handleSubmit(search)}>
        <label>
          在庫種別
          <select {...register("inventory_kind")}>
            <option value="">すべて</option>
            <option value="RAW_MATERIAL">原料</option>
            <option value="PRODUCT">製品</option>
          </select>
        </label>
        <label>
          取引種別
          <select {...register("transaction_type")}>
            <option value="">すべて</option>
            {[
              "RECEIPT",
              "MANUFACTURING_CONSUMPTION",
              "MANUFACTURING_OUTPUT",
              "SHIPMENT",
            ].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        {(["tea_leaf_id", "variety_id", "product_id"] as const).map((field) => (
          <label key={field}>
            {field}
            <input type="number" min="1" {...register(field)} />
          </label>
        ))}
        <label>
          開始日
          <input type="date" {...register("date_from")} />
        </label>
        <label>
          終了日
          <input type="date" {...register("date_to")} />
        </label>
        <button>検索</button>
      </form>
      {query.isPending && <p role="status">在庫履歴を取得中</p>}
      {query.isError && <p role="alert">在庫履歴の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>在庫履歴はありません</p>}
      {query.data?.items.map((item) => (
        <article key={item.id}>
          {item.transaction_type} / {item.target_code} {item.target_name} /{" "}
          {item.quantity_delta.toFixed(3)} kg / 残高{" "}
          {item.balance_after.toFixed(3)} kg
        </article>
      ))}
      {query.data && (
        <Pagination page={page} totalPages={query.data.total_pages} />
      )}
    </section>
  );
}

export function ShipmentListPage() {
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const query = useQuery({
    queryKey: ["shipments", page],
    queryFn: () => fetchShipments(page, 20),
  });
  return (
    <section>
      <h1>出荷一覧</h1>
      <Link to="/shipments/new">出荷登録</Link>
      {query.isPending && <p role="status">出荷を取得中</p>}
      {query.isError && <p role="alert">出荷の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>出荷はありません</p>}
      {query.data?.items.map((shipment) => (
        <article key={shipment.id}>
          <Link to={`/shipments/${shipment.id}`}>
            {shipment.shipment_number}
          </Link>{" "}
          / 状態: {shipment.status} / {shipment.shipped_date}
        </article>
      ))}
      {query.data && (
        <Pagination page={page} totalPages={query.data.total_pages} />
      )}
    </section>
  );
}

function ShipmentEditor({ shipment }: { shipment?: Shipment }) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const products = useQuery({
    queryKey: ["masters", "products"],
    queryFn: () => fetchMasters("products"),
  });
  const form = useForm<ShipmentInput>({
    defaultValues: shipment
      ? {
          shipment_number: shipment.shipment_number,
          shipped_date: shipment.shipped_date,
          lines: shipment.lines.map((line) => ({
            product_id: line.product_id,
            quantity: line.quantity.toFixed(3),
          })),
        }
      : { lines: [{ product_id: 0, quantity: "0.001" }] },
  });
  const lines = useFieldArray({ control: form.control, name: "lines" });
  const mutation = useMutation({
    mutationFn: (value: ShipmentInput) =>
      shipment ? updateShipment(shipment.id, value) : createShipment(value),
    onSuccess: (saved) => {
      client.invalidateQueries({ queryKey: ["shipments"] });
      client.setQueryData(["shipment", String(saved.id)], saved);
      if (!shipment) navigate(`/shipments/${saved.id}`);
    },
  });
  if (products.isPending) return <p role="status">製品を取得中</p>;
  if (products.isError) return <p role="alert">製品の取得に失敗しました</p>;
  return (
    <form onSubmit={form.handleSubmit((value) => mutation.mutate(value))}>
      {mutation.isError && <p role="alert">出荷の保存に失敗しました</p>}
      <label>
        出荷番号
        <input {...form.register("shipment_number", { required: true })} />
      </label>
      <label>
        出荷日
        <input
          type="date"
          {...form.register("shipped_date", { required: true })}
        />
      </label>
      {lines.fields.map((field, index) => (
        <fieldset key={field.id}>
          <legend>出荷明細 {index + 1}</legend>
          <label>
            製品
            <select
              {...form.register(`lines.${index}.product_id`, {
                valueAsNumber: true,
                min: 1,
              })}
            >
              <option value="0">選択</option>
              {products.data
                ?.filter((item) => item.is_active)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            出荷数量 (kg)
            <input
              type="number"
              min="0.001"
              step="0.001"
              {...form.register(`lines.${index}.quantity`, {
                required: true,
                min: 0.001,
              })}
            />
          </label>
          {lines.fields.length > 1 && (
            <button type="button" onClick={() => lines.remove(index)}>
              明細削除
            </button>
          )}
        </fieldset>
      ))}
      <button
        type="button"
        onClick={() => lines.append({ product_id: 0, quantity: "0.001" })}
      >
        明細追加
      </button>
      <button disabled={mutation.isPending}>
        {mutation.isPending ? "保存中" : "保存"}
      </button>
    </form>
  );
}

export function ShipmentFormPage() {
  return (
    <section>
      <h1>出荷登録</h1>
      <ShipmentEditor />
    </section>
  );
}

export function ShipmentDetailPage() {
  const { shipmentId = "" } = useParams();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["shipment", shipmentId],
    queryFn: () => fetchShipment(shipmentId),
  });
  const confirm = useMutation({
    mutationFn: (id: number) => confirmShipment(id),
    onSuccess: (shipment) => {
      client.setQueryData(["shipment", shipmentId], shipment);
      client.invalidateQueries({ queryKey: ["shipments"] });
      client.invalidateQueries({ queryKey: ["inventory-balances"] });
      client.invalidateQueries({ queryKey: ["inventory-transactions"] });
    },
  });
  return (
    <section>
      <h1>出荷詳細</h1>
      {query.isPending && <p role="status">出荷詳細を取得中</p>}
      {query.isError && <p role="alert">出荷詳細の取得に失敗しました</p>}
      {confirm.isError && <p role="alert">出荷確定に失敗しました</p>}
      {query.data && (
        <>
          <p>{query.data.shipment_number}</p>
          <p>状態: {query.data.status}</p>
          {query.data.lines.map((line) => (
            <p key={line.id}>
              {line.product_name}: {line.quantity.toFixed(3)} kg
            </p>
          ))}
          {query.data.status === "DRAFT" ? (
            <>
              <button
                disabled={confirm.isPending}
                onClick={() => confirm.mutate(query.data.id)}
              >
                {confirm.isPending ? "確定中" : "出荷確定"}
              </button>
              <h2>下書き編集</h2>
              <ShipmentEditor shipment={query.data} />
            </>
          ) : (
            <p>確定済みのため読み取り専用です。</p>
          )}
        </>
      )}
    </section>
  );
}

function PeriodForm({
  dateFrom,
  dateTo,
  onChange,
}: {
  dateFrom: string;
  dateTo: string;
  onChange: (from: string, to: string) => void;
}) {
  const form = useForm({
    defaultValues: { date_from: dateFrom, date_to: dateTo },
  });
  return (
    <form
      onSubmit={form.handleSubmit((value) =>
        onChange(value.date_from, value.date_to),
      )}
    >
      <label>
        開始日
        <input
          type="date"
          {...form.register("date_from", { required: true })}
        />
      </label>
      <label>
        終了日
        <input type="date" {...form.register("date_to", { required: true })} />
      </label>
      <button>期間更新</button>
    </form>
  );
}

export function ReportsPage() {
  const defaults = defaultPeriod();
  const [params, setParams] = useSearchParams();
  const dateFrom = params.get("date_from") ?? defaults.dateFrom;
  const dateTo = params.get("date_to") ?? defaults.dateTo;
  const valid = dateFrom <= dateTo;
  const query = useQuery({
    queryKey: ["summary", dateFrom, dateTo],
    queryFn: () => fetchSummary(dateFrom, dateTo),
    enabled: valid,
  });
  return (
    <section>
      <h1>期間集計</h1>
      <PeriodForm
        dateFrom={dateFrom}
        dateTo={dateTo}
        onChange={(from, to) => setParams({ date_from: from, date_to: to })}
      />
      {!valid && <p role="alert">開始日は終了日以前にしてください</p>}
      {query.isPending && valid && <p role="status">集計を取得中</p>}
      {query.isError && <p role="alert">集計の取得に失敗しました</p>}
      {query.data && (
        <>
          <p>入荷合計: {query.data.receipt_quantity.toFixed(3)} kg</p>
          <p>製造完了合計: {query.data.manufacturing_quantity.toFixed(3)} kg</p>
          <p>確定出荷合計: {query.data.shipment_quantity.toFixed(3)} kg</p>
          {query.data.receipt_breakdown.length === 0 &&
            query.data.manufacturing_breakdown.length === 0 &&
            query.data.shipment_breakdown.length === 0 && (
              <p>期間内データはありません</p>
            )}
          {[
            ...query.data.receipt_breakdown,
            ...query.data.manufacturing_breakdown,
            ...query.data.shipment_breakdown,
          ].map((item, index) => (
            <p key={`${item.code}-${index}`}>
              {item.code} {item.name}: {item.quantity.toFixed(3)} kg
            </p>
          ))}
        </>
      )}
    </section>
  );
}

export function DashboardPanel() {
  const initial = defaultPeriod();
  const [period, setPeriod] = useState(initial);
  const [invalid, setInvalid] = useState(false);
  const query = useQuery({
    queryKey: ["dashboard", period.dateFrom, period.dateTo],
    queryFn: () => fetchDashboard(period.dateFrom, period.dateTo),
  });
  const change = (dateFrom: string, dateTo: string) => {
    setInvalid(dateFrom > dateTo);
    if (dateFrom <= dateTo) setPeriod({ dateFrom, dateTo });
  };
  return (
    <section>
      <h2>ダッシュボード</h2>
      <PeriodForm
        dateFrom={period.dateFrom}
        dateTo={period.dateTo}
        onChange={change}
      />
      {invalid && <p role="alert">開始日は終了日以前にしてください</p>}
      {query.isPending && <p role="status">ダッシュボードを取得中</p>}
      {query.isError && <p role="alert">ダッシュボードの取得に失敗しました</p>}
      {query.data && (
        <>
          {Object.entries(query.data.manufacturing_status_counts).map(
            ([status, count]) => (
              <p key={status}>
                製造状態 {status}: {count}件
              </p>
            ),
          )}
          <p>
            原料在庫:{" "}
            {query.data.raw_material_inventory.total_quantity.toFixed(3)} kg（
            {query.data.raw_material_inventory.item_count}件）
          </p>
          <p>
            製品在庫: {query.data.product_inventory.total_quantity.toFixed(3)}{" "}
            kg（
            {query.data.product_inventory.item_count}件）
          </p>
          <p>期間入荷: {query.data.receipt_quantity.toFixed(3)} kg</p>
          <p>期間製造完了: {query.data.manufacturing_quantity.toFixed(3)} kg</p>
          <p>期間確定出荷: {query.data.shipment_quantity.toFixed(3)} kg</p>
        </>
      )}
    </section>
  );
}
