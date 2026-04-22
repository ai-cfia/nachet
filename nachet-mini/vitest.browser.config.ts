import { defineConfig, mergeConfig } from "vitest/config";
import { playwright } from "@vitest/browser-playwright";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      browser: {
        enabled: true,
        provider: playwright(),
        instances: [{ browser: "chromium" }],
        headless: true,
      },
      include: ["src/inference/tests/**/*.test.ts"],
      coverage: {
        provider: "v8",
        include: ["src/inference/*.ts"],
        // worker.ts runs in a Web Worker context (separate V8 isolate) and
        // cannot be instrumented by the main-thread coverage collector.
        exclude: ["src/inference/worker.ts", "src/inference/tests/**"],
      },
    },
  }),
);
