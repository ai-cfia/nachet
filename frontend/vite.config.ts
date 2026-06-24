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
  html: {
    cspNonce: "__CSP_NONCE__", // Placeholder for CSP nonce (replaced by backend at runtime)
  },
  resolve: {
    alias: {
      "@common": path.resolve(__dirname, "./src/common"),
      "@common/*": path.resolve(__dirname, "./src/common/*"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@hooks/*": path.resolve(__dirname, "./src/hooks/*"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@components/*": path.resolve(__dirname, "./src/components/*"),
      "@styles": path.resolve(__dirname, "./src/styles"),
      "@styles/*": path.resolve(__dirname, "./src/styles/*"),
      "@stores": path.resolve(__dirname, "./src/stores"),
      "@stores/*": path.resolve(__dirname, "./src/stores/*"),
      "oidc-client-ts": path.resolve(
        __dirname,
        "./submodules/oidc-client-ts/dist/esm/oidc-client-ts.js",
      ),
    },
  },
});
