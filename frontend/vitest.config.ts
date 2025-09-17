import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    // Specify other Vitest options here
  },
  resolve: {
    alias: {
      "@common": path.resolve(__dirname, "./src/common"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
    },
  },
});
