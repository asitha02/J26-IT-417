
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8000";
const paths = ["/health", "/ingest", "/fusion", "/kb", "/generate", "/translate", "/export"];

export default defineConfig({
  plugins: [react()],
  server: { proxy: Object.fromEntries(paths.map((p) => [p, backend])) },
});