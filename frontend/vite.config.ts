import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import EnvironmentPlugin from "vite-plugin-environment";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    EnvironmentPlugin("all"), // include all environment variables
  ],
  define: {
    "process.env": {},
  },
  resolve: {
    alias: {
      "@common": path.resolve(__dirname, "./src/common"),
    },
  },
});
