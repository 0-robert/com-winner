import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    port: 5173,
    proxy: {
      // All /api/* requests → unified backend on :8000 (strips /api prefix)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api/config-status": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/config-status/, "/config-status"),
      },
      "/api/batch-receipts": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/batch-receipts/, "/batch-receipts"),
      },
      "/api/batch": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/batch/, "/batch"),
      },
    },
  },
});
