import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O front-end conversa com o backend FastAPI. Em desenvolvimento, as chamadas
// para /api são redirecionadas (proxy) para http://localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
