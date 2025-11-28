import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  envDir: "..",
  define: {
    // Expose Vercel system environment variables for preview deployment detection
    "import.meta.env.VERCEL_ENV": JSON.stringify(process.env.VERCEL_ENV),
    "import.meta.env.VERCEL_GIT_COMMIT_REF": JSON.stringify(
      process.env.VERCEL_GIT_COMMIT_REF
    ),
    // Bypass secret for accessing protected preview deployments
    "import.meta.env.VERCEL_AUTOMATION_BYPASS_SECRET": JSON.stringify(
      process.env.VERCEL_AUTOMATION_BYPASS_SECRET
    ),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
