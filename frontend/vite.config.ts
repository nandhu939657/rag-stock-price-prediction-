import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Single .env file lives at the repo root, shared with the backend (see
  // backend/app/config.py). Vite only ever exposes VITE_-prefixed variables to
  // the client bundle - everything else in that file (backend secrets) is
  // automatically excluded, so this is safe even though it's the same file.
  envDir: "..",
  server: {
    port: 5173,
  },
});
