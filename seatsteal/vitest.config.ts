import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    css: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "json-summary", "html", "lcov"],
      exclude: [
        "node_modules/",
        "src/test/",
        "**/*.test.{js,mjs,cjs,ts,mts,cts,jsx,tsx}",
        "**/*.spec.{js,mjs,cjs,ts,mts,cts,jsx,tsx}",
        "**/*.config.{js,ts}",
        "**/dist/",
        "**/build/",
        "**/.{idea,git,cache,output,temp}/",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
