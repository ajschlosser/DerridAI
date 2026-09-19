import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "happy-dom",
    setupFiles: ["./tests/frontend/setup.ts"],
    include: ["tests/frontend/**/*.test.ts"],
    restoreMocks: true,
    clearMocks: true,
  },
});
