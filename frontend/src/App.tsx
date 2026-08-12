import { useQuery } from "@tanstack/react-query";
import { Route, Routes } from "react-router-dom";

import { fetchHealth } from "./api/health";

function HealthPage() {
  const healthQuery = useQuery({
    queryKey: ["backend-health"],
    queryFn: fetchHealth,
    retry: false,
  });

  return (
    <main className="app-shell">
      <section className="status-card" aria-labelledby="system-title">
        <p className="eyebrow">TEA-V1</p>
        <h1 id="system-title">お茶製造管理システム</h1>
        {healthQuery.isPending && <p role="status">backend health取得中</p>}
        {healthQuery.isSuccess && (
          <p role="status" className="status-success">
            backend health成功: {healthQuery.data.status}
          </p>
        )}
        {healthQuery.isError && (
          <p role="alert" className="status-error">
            backend health失敗
          </p>
        )}
      </section>
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="*" element={<HealthPage />} />
    </Routes>
  );
}
