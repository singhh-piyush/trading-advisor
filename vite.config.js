import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://<user>.github.io/trading-advisor/ so assets need the
// repo-name base path. Data is fetched at runtime from the raw GitHub URL.
export default defineConfig({
  base: "/trading-advisor/",
  plugins: [react()],
});
