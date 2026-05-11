import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    env: {
      // Set MCP port to something that will give instant connection refused
      AHS_MCP_PORT: "1",
    },
    testTimeout: 10_000,
  },
});
