import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "lucide-react": path.resolve(__dirname, "node_modules/lucide-react"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/tests/setupTests.js",
    include: ["src/tests/**/*.test.{js,jsx}"],
    css: true,
  },
});
