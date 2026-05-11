// ============================================================
// AHS TypeScript Core — Gateway Tests
// ============================================================

import { describe, it, expect, vi } from "vitest";
import * as http from "node:http";
import { GatewayServer } from "../src/gateway.js";
import { AHEngine } from "../src/orchestrator/index.js";

/**
 * Helper: send an HTTP request to a running gateway.
 */
function request(
  server: http.Server,
  method: string,
  path: string,
  body?: string,
): Promise<{ status: number; data: unknown; headers: http.IncomingHttpHeaders }> {
  return new Promise((resolve, reject) => {
    const addr = server.address();
    if (!addr || typeof addr === "string") {
      reject(new Error("Server not listening"));
      return;
    }

    const options: http.RequestOptions = {
      hostname: "127.0.0.1",
      port: addr.port,
      path,
      method,
      headers: { "Content-Type": "application/json" },
    };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk: string) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode || 0, data: JSON.parse(data), headers: res.headers });
        } catch {
          resolve({ status: res.statusCode || 0, data: data, headers: res.headers });
        }
      });
    });

    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

describe("GatewayServer", () => {
  let gateway: GatewayServer;
  let engine: AHEngine;
  let port: number;

  it("creates gateway with config", () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine); // port 0 = random
    const status = gateway.getStatus();
    expect(status.running).toBe(false);
    expect(status.port).toBe(0);
    expect(status.version).toBe("0.4.0");
  });

  it("starts and stops on random port", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const status = gateway.getStatus();
    expect(status.running).toBe(true);
    expect(status.uptime).toBeGreaterThanOrEqual(0);

    await gateway.stop();
    expect(gateway.getStatus().running).toBe(false);
  });

  it("returns 200 on /health", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const addr = gateway["server"]?.address();
    port = (addr as { port: number }).port;

    const res = await request(gateway["server"]!, "GET", "/health");
    expect(res.status).toBe(200);
    expect((res.data as { status: string }).status).toBe("ok");
    expect((res.data as { version: string }).version).toBe("0.4.0");

    await gateway.stop();
  });

  it("returns 200 on /status with system info", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "GET", "/status");
    expect(res.status).toBe(200);
    const data = res.data as Record<string, unknown>;
    expect(data).toHaveProperty("platform");
    expect(data).toHaveProperty("hostname");
    expect(data).toHaveProperty("node");
    expect(data).toHaveProperty("memory");

    await gateway.stop();
  });

  it("returns 200 on /task with valid JSON body", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "POST", "/task", JSON.stringify({ task: "مرحبا", mode: "quick" }));
    expect(res.status).toBe(200);
    const data = res.data as Record<string, unknown>;
    expect(data.success).toBe(true);

    await gateway.stop();
  });

  it("returns 400 on /task with missing task field", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "POST", "/task", JSON.stringify({}));
    expect(res.status).toBe(400);
    const data = res.data as Record<string, unknown>;
    expect(data.error).toBeTruthy();

    await gateway.stop();
  });

  it("returns 405 on GET /task", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "GET", "/task");
    expect(res.status).toBe(405);

    await gateway.stop();
  });

  it("returns 404 on unknown path", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "GET", "/nonexistent");
    expect(res.status).toBe(404);

    await gateway.stop();
  });

  it("returns 204 on OPTIONS (CORS preflight)", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "OPTIONS", "/health");
    expect(res.status).toBe(204);

    await gateway.stop();
  });

  it("handles deep/hybrid mode tasks", { timeout: 10_000 }, async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    // Use a task that will fail fast (Hermes not running)
    const res = await request(
      gateway["server"]!,
      "POST",
      "/task",
      JSON.stringify({ task: "hi", mode: "hybrid" }),
    );
    // Should still return a response even if Hermes is down
    expect(res.status).toBe(200);

    await gateway.stop();
  });

  it("tracks tasks processed", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    await request(gateway["server"]!, "POST", "/task", JSON.stringify({ task: "test", mode: "quick" }));
    const status = gateway.getStatus();
    expect(status.tasksProcessed).toBe(1);

    await request(gateway["server"]!, "POST", "/task", JSON.stringify({ task: "test2", mode: "quick" }));
    const status2 = gateway.getStatus();
    expect(status2.tasksProcessed).toBe(2);

    await gateway.stop();
  });

  it("handles malformed JSON gracefully", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    const res = await request(gateway["server"]!, "POST", "/task", "not-json");
    expect(res.status).toBe(500); // or 400 depending on error location

    await gateway.stop();
  });

  it("returns /logs endpoint", async () => {
    engine = new AHEngine();
    gateway = new GatewayServer({ port: 0 }, engine);
    await gateway.start();

    // Make a request first so we have a log entry
    await request(gateway["server"]!, "GET", "/health");

    const res = await request(gateway["server"]!, "GET", "/logs");
    expect(res.status).toBe(200);
    const data = res.data as { recent: unknown[]; stats: unknown };
    expect(Array.isArray(data.recent)).toBe(true);
    expect(data.stats).toHaveProperty("total");

    await gateway.stop();
  });
});
