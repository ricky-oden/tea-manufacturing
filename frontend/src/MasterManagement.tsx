import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useSearchParams } from "react-router-dom";

import {
  createMaster,
  fetchMasterPage,
  fetchMasters,
  updateMaster,
  type Master,
  type MasterInput,
  type MasterResource,
} from "./api/manufacturing";

const labels: Record<MasterResource, string> = {
  "tea-leaves": "茶葉",
  varieties: "品種",
  suppliers: "仕入先",
  equipment: "設備",
  products: "製品",
};

export function MasterManagementPage({
  resource,
}: {
  resource: MasterResource;
}) {
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const [editing, setEditing] = useState<Master | null>(null);
  const query = useQuery({
    queryKey: ["master-page", resource, page],
    queryFn: () => fetchMasterPage(resource, page, 20),
  });
  const varieties = useQuery({
    queryKey: ["masters", "varieties"],
    queryFn: () => fetchMasters("varieties"),
    enabled: resource === "products",
  });
  const { register, handleSubmit, reset } = useForm<MasterInput>({
    defaultValues: { code: "", name: "", is_active: true },
  });
  const mutation = useMutation({
    mutationFn: (value: MasterInput) =>
      editing
        ? updateMaster(resource, editing.id, value)
        : createMaster(resource, value),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["master-page", resource] });
      void client.invalidateQueries({ queryKey: ["masters", resource] });
      setEditing(null);
      reset({ code: "", name: "", is_active: true });
    },
  });
  const label = labels[resource];
  return (
    <section>
      <h1>{label}マスタ管理</h1>
      {query.isPending && <p role="status">{label}を取得中</p>}
      {query.isError && <p role="alert">{label}の取得に失敗しました</p>}
      {query.data?.items.length === 0 && <p>{label}はありません</p>}
      {mutation.isError && <p role="alert">{label}の保存に失敗しました</p>}
      {query.data?.items.map((item) => (
        <article key={item.id}>
          <strong>{item.code}</strong> / {item.name} /{" "}
          {item.is_active ? "有効" : "無効"}
          {item.variety_id && <span> / 品種ID: {item.variety_id}</span>}
          <button
            onClick={() => {
              setEditing(item);
              reset({
                code: item.code,
                name: item.name,
                is_active: item.is_active,
                variety_id: item.variety_id,
              });
            }}
          >
            編集
          </button>
          <button
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate({
                code: item.code,
                name: item.name,
                is_active: !item.is_active,
                variety_id: item.variety_id,
              })
            }
          >
            {item.is_active ? "無効にする" : "有効にする"}
          </button>
        </article>
      ))}
      {query.data && query.data.total_pages > 0 && (
        <nav aria-label={`${label}ページング`}>
          <button
            disabled={page <= 1}
            onClick={() => setParams({ page: String(page - 1) })}
          >
            前へ
          </button>
          <span>
            {page} / {query.data.total_pages}
          </span>
          <button
            disabled={page >= query.data.total_pages}
            onClick={() => setParams({ page: String(page + 1) })}
          >
            次へ
          </button>
        </nav>
      )}
      <form onSubmit={handleSubmit((value) => mutation.mutate(value))}>
        <h2>{editing ? `${label}編集` : `${label}登録`}</h2>
        <label>
          {label}コード
          <input {...register("code", { required: true })} />
        </label>
        <label>
          {label}名
          <input {...register("name", { required: true })} />
        </label>
        {resource === "products" && (
          <label>
            品種
            <select
              {...register("variety_id", { valueAsNumber: true, min: 1 })}
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
        )}
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
