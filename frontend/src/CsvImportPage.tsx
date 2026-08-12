import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import {
  productImportErrorCsvUrl,
  uploadProductsCsv,
  type CsvImportJob,
} from "./api/csvImports";

export function CsvImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<CsvImportJob | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const mutation = useMutation({
    mutationFn: uploadProductsCsv,
    onSuccess: (job) => {
      setResult(job);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    },
  });
  return (
    <section>
      <h1>製品マスタCSV取込</h1>
      <p>ヘッダー: product_code,product_name,variety_code,is_active</p>
      <p>UTF-8またはUTF-8 BOM付き、最大1 MiB、最大1,000データ行です。</p>
      <label>
        CSVファイル
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <button
        disabled={!file || mutation.isPending}
        onClick={() => file && mutation.mutate(file)}
      >
        {mutation.isPending ? "取込処理中" : "アップロード"}
      </button>
      {mutation.isError && (
        <p role="alert">CSV取込APIの呼び出しに失敗しました</p>
      )}
      {result && (
        <section aria-label="取込結果">
          <h2>取込結果</h2>
          <p>状態: {result.status}</p>
          <p>総行数: {result.total_rows}</p>
          <p>成功件数: {result.success_rows}</p>
          <p>失敗件数: {result.error_rows}</p>
          {result.errors.length > 0 && (
            <>
              <h3>エラー一覧</h3>
              {result.errors.map((error, index) => (
                <article
                  key={`${error.row_number}-${error.field_name}-${error.error_code}-${index}`}
                >
                  行{error.row_number} / {error.field_name || "ファイル"} /{" "}
                  {error.error_code} / {error.error_message} / 入力値:{" "}
                  {error.input_value}
                </article>
              ))}
            </>
          )}
          {result.error_csv_available && (
            <a href={productImportErrorCsvUrl(result.id)} download>
              エラーCSVをダウンロード
            </a>
          )}
        </section>
      )}
    </section>
  );
}
