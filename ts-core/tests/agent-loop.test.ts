// ============================================================
// AHS TypeScript Core — Agent Loop Tests
// ============================================================

import { describe, it, expect, vi } from "vitest";
import { AgentLoop } from "../src/agent-loop.js";

const TEST_ENDPOINT = `http://localhost:${process.env.AHS_MCP_PORT || "1"}`;

describe("AgentLoop", () => {
  it("creates with default config", () => {
    const loop = new AgentLoop();
    const status = loop.getStatus();
    expect(status.running).toBe(false);
    expect(status.tasksProcessed).toBe(0);
    expect(status.tasksInQueue).toBe(0);
    expect(status.healthStatus).toBe("degraded");
  });

  it("creates with custom config", () => {
    const loop = new AgentLoop({
      heartbeatMs: 10_000,
      maxQueueSize: 50,
      hermesEndpoint: TEST_ENDPOINT,
    });
    const status = loop.getStatus();
    expect(status.running).toBe(false);
  });

  it("start sets running to true", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    expect(loop.getStatus().running).toBe(true);
    await loop.stop();
    expect(loop.getStatus().running).toBe(false);
  });

  it("returns error when processing while stopped", async () => {
    const loop = new AgentLoop();
    const result = await loop.process("test");
    expect(result.success).toBe(false);
    expect(result.error).toBe("not_running");
  });

  it("processes quick mode tasks", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    const result = await loop.process("مرحبا", "quick");
    expect(result.success).toBe(true);
    expect(result.steps).toBe(1);
    await loop.stop();
  });

  it("tracks tasks processed", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    await loop.process("task1", "quick");
    await loop.process("task2", "quick");
    expect(loop.getStatus().tasksProcessed).toBe(2);
    await loop.stop();
  });

  it("execute bypasses queue", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    const result = await loop.execute("hello", "quick");
    expect(result.success).toBe(true);
    await loop.stop();
  });

  it("has bridge instance accessible", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    const bridge = loop.bridgeInstance;
    expect(bridge).toBeDefined();
    expect(bridge.getStatus().connected).toBe(true);
    await loop.stop();
  });

  it("updates lastTask on execution", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    await loop.process("write some code", "quick");
    expect(loop.getStatus().lastTask).toContain("write some code");
    await loop.stop();
  });

  it("handles multiple start/stop cycles", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    await loop.stop();
    await loop.start();
    expect(loop.getStatus().running).toBe(true);
    await loop.stop();
  });

  it("stop is safe to call multiple times", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.stop();
    await loop.stop();
    expect(loop.getStatus().running).toBe(false);
  });

  it("process queued task when busy", async () => {
    const loop = new AgentLoop({ heartbeatMs: 5000, hermesEndpoint: TEST_ENDPOINT });
    await loop.start();
    const p1 = loop.process("first");
    const p2 = loop.process("second");
    const [r1, r2] = await Promise.all([p1, p2]);
    expect(r1.success).toBe(true);
    expect((r2 as { success: boolean }).success).toBe(true);
    await loop.stop();
  });
});
