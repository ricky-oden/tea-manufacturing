import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";

import { fetchMasters, type ManufacturingStatus } from "./api/manufacturing";
import {
  createEquipment,
  createReceipt,
  fetchEquipment,
  fetchReceipt,
  fetchProcesses,
  fetchReceipts,
  processActionsFor,
  updateEquipment,
  updateProcess,
  type EquipmentInput,
  type ReceiptInput,
} from "./api/phase3";

export function ReceiptListPage() {
  const query = useQuery({
    queryKey: ["raw-material-receipts", 1],
    queryFn: () => fetchReceipts(1, 20),
  });
  return (
    <section>
      <h1>原料入荷一覧</h1>
      <Link to="/raw-material-receipts/new">入荷登録</Link>
      {query.isPending && <p role="status">原料入荷を取得中</p>}
      {query.isError && <p role="alert">原料入荷の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>原料入荷はありません</p>}
      {query.data?.items.map((receipt) => (
        <article key={receipt.id}>
          <Link to={`/raw-material-receipts/${receipt.id}`}>
            {receipt.receipt_number}
          </Link>{" "}
          / {receipt.received_date} / {receipt.supplier_name} /{" "}
          {receipt.lines.length}明細
        </article>
      ))}
    </section>
  );
}

export function ReceiptDetailPage() {
  const { receiptId = "" } = useParams();
  const query = useQuery({
    queryKey: ["raw-material-receipt", receiptId],
    queryFn: () => fetchReceipt(receiptId),
  });
  return (
    <section>
      <h1>原料入荷詳細</h1>
      {query.isPending && <p role="status">原料入荷詳細を取得中</p>}
      {query.isError && <p role="alert">原料入荷詳細の取得に失敗しました</p>}
      {query.data && (
        <>
          <p>{query.data.receipt_number}</p>
          <p>入荷日: {query.data.received_date}</p>
          <p>仕入先: {query.data.supplier_name}</p>
          {query.data.lines.map((line) => (
            <p key={line.id}>
              {line.tea_leaf_name} / {line.variety_name} /{" "}
              {line.quantity.toFixed(3)} kg
            </p>
          ))}
        </>
      )}
    </section>
  );
}

export function ReceiptFormPage() {
  const client = useQueryClient();
  const suppliers = useQuery({
    queryKey: ["masters", "suppliers"],
    queryFn: () => fetchMasters("suppliers"),
  });
  const teaLeaves = useQuery({
    queryKey: ["masters", "tea-leaves"],
    queryFn: () => fetchMasters("tea-leaves"),
  });
  const varieties = useQuery({
    queryKey: ["masters", "varieties"],
    queryFn: () => fetchMasters("varieties"),
  });
  const { register, control, handleSubmit, formState } = useForm<ReceiptInput>({
    defaultValues: {
      lines: [{ tea_leaf_id: 0, variety_id: 0, quantity: "0.001" }],
    },
  });
  const lines = useFieldArray({ control, name: "lines" });
  const mutation = useMutation({
    mutationFn: createReceipt,
    onSuccess: () =>
      client.invalidateQueries({ queryKey: ["raw-material-receipts"] }),
  });
  const queries = [suppliers, teaLeaves, varieties];
  if (queries.some((query) => query.isPending))
    return <p role="status">マスタを取得中</p>;
  if (queries.some((query) => query.isError))
    return <p role="alert">マスタの取得に失敗しました</p>;
  return (
    <section>
      <h1>原料入荷登録</h1>
      {mutation.isSuccess && <p role="status">原料入荷を登録しました</p>}
      {mutation.isError && <p role="alert">原料入荷の登録に失敗しました</p>}
      <form onSubmit={handleSubmit((value) => mutation.mutate(value))}>
        <label>
          入荷番号
          <input {...register("receipt_number", { required: true })} />
        </label>
        <label>
          入荷日
          <input
            type="date"
            {...register("received_date", { required: true })}
          />
        </label>
        <label>
          仕入先
          <select {...register("supplier_id", { valueAsNumber: true, min: 1 })}>
            <option value="0">選択</option>
            {suppliers.data
              ?.filter((item) => item.is_active)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
          </select>
        </label>
        {lines.fields.map((field, index) => (
          <fieldset key={field.id}>
            <legend>入荷明細 {index + 1}</legend>
            <label>
              茶葉
              <select
                {...register(`lines.${index}.tea_leaf_id`, {
                  valueAsNumber: true,
                  min: 1,
                })}
              >
                <option value="0">選択</option>
                {teaLeaves.data
                  ?.filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              品種
              <select
                {...register(`lines.${index}.variety_id`, {
                  valueAsNumber: true,
                  min: 1,
                })}
              >
                <option value="0">選択</option>
                {varieties.data
                  ?.filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              入荷数量 (kg)
              <input
                type="number"
                step="0.001"
                min="0.001"
                {...register(`lines.${index}.quantity`, {
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
          onClick={() =>
            lines.append({ tea_leaf_id: 0, variety_id: 0, quantity: "0.001" })
          }
        >
          明細追加
        </button>
        <button disabled={mutation.isPending || formState.isSubmitting}>
          {mutation.isPending ? "登録中" : "入荷登録"}
        </button>
      </form>
    </section>
  );
}

export function ProcessPanel({
  orderId,
  orderStatus,
}: {
  orderId: number;
  orderStatus: ManufacturingStatus;
}) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["manufacturing-processes", orderId],
    queryFn: () => fetchProcesses(orderId),
  });
  const mutation = useMutation({
    mutationFn: ({
      processId,
      action,
    }: {
      processId: number;
      action: "start" | "complete";
    }) => updateProcess(orderId, processId, action),
    onSuccess: () =>
      client.invalidateQueries({
        queryKey: ["manufacturing-processes", orderId],
      }),
  });
  return (
    <section>
      <h2>製造工程</h2>
      {query.isPending && <p role="status">工程を取得中</p>}
      {query.isError && <p role="alert">工程の取得に失敗しました</p>}
      {mutation.isError && <p role="alert">工程操作に失敗しました</p>}
      {query.data?.length === 0 && <p>工程はありません</p>}
      {query.data?.map((process) => (
        <article key={process.id}>
          {process.sequence}. {process.process_name} / {process.status}
          {processActionsFor(orderStatus, process).map((action) => (
            <button
              key={action}
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ processId: process.id, action })}
            >
              {action === "start" ? "工程開始" : "工程完了"}
            </button>
          ))}
        </article>
      ))}
    </section>
  );
}

export function EquipmentPage() {
  const client = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const query = useQuery({ queryKey: ["equipment"], queryFn: fetchEquipment });
  const { register, handleSubmit, reset } = useForm<EquipmentInput>({
    defaultValues: { code: "", name: "", is_active: true },
  });
  const mutation = useMutation({
    mutationFn: ({
      id,
      value,
    }: {
      id: number | null;
      value: EquipmentInput;
    }) => (id === null ? createEquipment(value) : updateEquipment(id, value)),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["equipment"] });
      client.invalidateQueries({ queryKey: ["masters", "equipment"] });
      setEditingId(null);
      reset({ code: "", name: "", is_active: true });
    },
  });
  return (
    <section>
      <h1>設備管理</h1>
      {query.isPending && <p role="status">設備を取得中</p>}
      {query.isError && <p role="alert">設備の取得に失敗しました</p>}
      {query.data?.length === 0 && <p>設備はありません</p>}
      {mutation.isError && <p role="alert">設備の保存に失敗しました</p>}
      {query.data?.map((equipment) => (
        <article key={equipment.id}>
          {equipment.code} / {equipment.name} /{" "}
          {equipment.is_active ? "有効" : "無効"}
          <button
            onClick={() => {
              setEditingId(equipment.id);
              reset({
                code: equipment.code,
                name: equipment.name,
                is_active: equipment.is_active,
              });
            }}
          >
            編集
          </button>
          <button
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate({
                id: equipment.id,
                value: {
                  code: equipment.code,
                  name: equipment.name,
                  is_active: !equipment.is_active,
                },
              })
            }
          >
            {equipment.is_active ? "無効にする" : "有効にする"}
          </button>
        </article>
      ))}
      <form
        onSubmit={handleSubmit((value) =>
          mutation.mutate({ id: editingId, value }),
        )}
      >
        <h2>{editingId === null ? "設備登録" : "設備編集"}</h2>
        <label>
          設備コード
          <input {...register("code", { required: true })} />
        </label>
        <label>
          設備名
          <input {...register("name", { required: true })} />
        </label>
        <label>
          <input type="checkbox" {...register("is_active")} /> 有効
        </label>
        <button disabled={mutation.isPending}>
          {mutation.isPending ? "保存中" : "保存"}
        </button>
      </form>
    </section>
  );
}
