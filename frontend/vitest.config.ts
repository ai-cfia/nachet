import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    exclude: ["node_modules/**", "dist/**", "vendor/**"],
    // Specify other Vitest options here
    coverage: {
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/tests/**",
        "src/**/index.{ts,tsx}",
        "src/**/*.config.{ts,tsx}",
        "src/**/types.{ts,tsx}",
        "src/**/testUtils.{ts,tsx}",
        "src/**/*.d.ts",
        "src/**/locales/**",
      ],
    },
  },
  resolve: {
    alias: {
      "@common": path.resolve(__dirname, "./src/common"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@styles": path.resolve(__dirname, "./src/styles"),
      "@common/*": path.resolve(__dirname, "./src/common/*"),
      "@hooks/*": path.resolve(__dirname, "./src/hooks/*"),
      "@components/*": path.resolve(__dirname, "./src/components/*"),
      "@styles/*": path.resolve(__dirname, "./src/styles/*"),
      "@stores": path.resolve(__dirname, "./src/stores"),
      "@stores/*": path.resolve(__dirname, "./src/stores/*"),
      "oidc-client-ts": path.resolve(
        __dirname,
        "./vendor/oidc-client-ts/src/index.ts",
      ),
    },
  },
});
