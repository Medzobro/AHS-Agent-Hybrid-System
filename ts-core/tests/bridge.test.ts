// ============================================================
// AHS TypeScript Core — Bridge Tests
// ============================================================

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { HermesBridge, MCPError, MCPSession } from "../src/bridge/hermes-bridge.js";

const TEST_HERMES_PORT = Number.parseInt(process.env.AHS_MCP_PORT || "1");
const TEST_ENDPOINT = `http://localhost:${TEST_HERMES_PORT}`;

describe("MCPError", () => {
  it("creates error with code and message", () => {
    const err = new MCPError(-32000, "Not connected");
    expect(err.code).toBe(-32000);
    expect(err.message).toBe("MCP Error -32000: Not connected");
    expect(err.name).toBe("MCPError");
  });

  it("carries optional data", () => {
    const err = new MCPError(-32603, "Internal error", { detail: "db_failure" });
    expect(err.data).toEqual({ detail: "db_failure" });
  });
});

describe("MCPSession", () => {
  let session: MCPSession;

  afterEach(async () => {
    await session?.disconnect().catch(() => {});
  });

  it("creates session with HTTP config", () => {
    session = new MCPSession({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });
    expect(session.isActive).toBe(false);
  });

  it("connect works even without Hermes", async () => {
    session = new MCPSession({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });
    await session.connect();
    expect(session.isActive).toBe(true);
  });

  it("disconnect rejects pending requests", async () => {
    session = new MCPSession({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });
    await session.connect();

    const callPromise = session.call("hermes/invoke", { task: "test" });
    await session.disconnect();
    await expect(callPromise).rejects.toThrow("Session disconnected");
  });

  it("throws on disconnected call", async () => {
    session = new MCPSession({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });

    await expect(session.call("test", {})).rejects.toThrow("Session not connected");
  });
});

describe("HermesBridge", () => {
  let bridge: HermesBridge;

  beforeEach(() => {
    bridge = new HermesBridge({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });
  });

  afterEach(async () => {
    await bridge?.disconnect().catch(() => {});
  });

  it("creates bridge with config", () => {
    const status = bridge.getStatus();
    expect(status.connected).toBe(false);
    expect(status.transport).toBe("http");
    expect(status.requestCount).toBe(0);
    expect(status.errorCount).toBe(0);
    expect(status.uptime).toBeGreaterThanOrEqual(0);
  });

  it("connects and disconnects", async () => {
    await bridge.connect();
    expect(bridge.getStatus().connected).toBe(true);
    await bridge.disconnect();
    expect(bridge.getStatus().connected).toBe(false);
  });

  it("sendTask returns error when Hermes is down", async () => {
    await bridge.connect();
    const result = await bridge.sendTask({ task: "hello", skills: [] });
    expect(result.success).toBe(false);
    expect(result.error).toBeTruthy();
    expect(result.elapsedMs).toBeGreaterThanOrEqual(0);
  });

  it("sendTask uses options.timeout", async () => {
    await bridge.connect();
    const result = await bridge.sendTask({ task: "hello", timeout: 500 });
    expect(result.success).toBe(false);
  });

  it("send is shorthand for sendTask", async () => {
    await bridge.connect();
    const result = await bridge.send("hello");
    expect(result).toHaveProperty("success");
    expect(result).toHaveProperty("content");
    expect(result).toHaveProperty("elapsedMs");
  });

  it("listTools returns empty array when Hermes is down", async () => {
    await bridge.connect();
    const tools = await bridge.listTools();
    expect(Array.isArray(tools)).toBe(true);
    expect(tools.length).toBe(0);
  });

  it("tracks request and error counts", async () => {
    await bridge.connect();
    await bridge.send("test1");
    await bridge.send("test2");
    await bridge.listTools();
    const status = bridge.getStatus();
    expect(status.requestCount).toBe(3);
    expect(status.errorCount).toBeGreaterThanOrEqual(2);
  });
});
