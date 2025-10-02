import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    // Specify other Vitest options here
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
    },
  },
});
