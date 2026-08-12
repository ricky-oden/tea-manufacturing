import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_PROXY_TARGET || "http://localhost:8001";

  return {
    define: {
      __API_BASE_URL__: JSON.stringify(env.VITE_API_BASE_URL || "/api/v1"),
    },
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api/v1": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
