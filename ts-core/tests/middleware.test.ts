// ============================================================
// AHS TypeScript Core — Middleware Tests
// ============================================================

import { describe, it, expect, vi } from "vitest";
import { IncomingMessage, ServerResponse } from "node:http";
import { Socket } from "node:net";
import {
  RateLimiter,
  RequestLogger,
  createErrorResponse,
  applyCORS,
  jsonResponse,
  jsonError,
} from "../src/middleware.js";

/** Create a minimal IncomingMessage for testing */
function makeReq(ip = "127.0.0.1", headers: Record<string, string> = {}): IncomingMessage {
  const socket = new Socket();
  const req = new IncomingMessage(socket);
  (req.socket as any).__remoteAddress = ip;
  req.headers = headers;
  // Override the private getter via Object.defineProperty
  Object.defineProperty(req.socket, "remoteAddress", {
    get: () => ip,
    configurable: true,
  });
  return req;
}

/** Create a minimal ServerResponse */
function makeRes(): ServerResponse {
  const socket = new Socket();
  return new ServerResponse(socket);
}

describe("RateLimiter", () => {
  it("allows requests under limit", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 5 });
    for (let i = 0; i < 5; i++) {
      expect(limiter.check(makeReq())).toBe(true);
    }
  });

  it("blocks requests over limit", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 3 });
    for (let i = 0; i < 3; i++) limiter.check(makeReq());
    expect(limiter.check(makeReq())).toBe(false);
  });

  it("resets after window expires", async () => {
    const limiter = new RateLimiter({ windowMs: 50, maxRequests: 2 });
    expect(limiter.check(makeReq())).toBe(true);
    expect(limiter.check(makeReq())).toBe(true);
    expect(limiter.check(makeReq())).toBe(false);

    // Wait for window to expire
    await new Promise((r) => setTimeout(r, 60));
    expect(limiter.check(makeReq())).toBe(true);
  });

  it("tracks blocked count", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 1 });
    limiter.check(makeReq());
    limiter.check(makeReq()); // blocked
    expect(limiter.getStats(makeReq()).blocked).toBe(1);
  });

  it("shows correct remaining count", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 5 });
    expect(limiter.getStats(makeReq()).remaining).toBe(5);
    limiter.check(makeReq());
    expect(limiter.getStats(makeReq()).remaining).toBe(4);
  });

  it("uses X-Forwarded-For when trustProxy is enabled", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 1, trustProxy: true });
    const req = makeReq("127.0.0.1", { "x-forwarded-for": "10.0.0.1" });
    limiter.check(req);
    const stats = limiter.getStats(req);
    expect(stats.current).toBe(1);
  });

  it("reset clears all state", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 1 });
    limiter.check(makeReq());
    limiter.check(makeReq()); // blocked
    limiter.reset();
    expect(limiter.getStats(makeReq()).blocked).toBe(0);
    expect(limiter.getStats(makeReq()).current).toBe(0);
  });

  it("treats different IPs separately", () => {
    const limiter = new RateLimiter({ windowMs: 1000, maxRequests: 1 });
    expect(limiter.check(makeReq("10.0.0.1"))).toBe(true);
    expect(limiter.check(makeReq("10.0.0.2"))).toBe(true);
    expect(limiter.check(makeReq("10.0.0.1"))).toBe(false);
    expect(limiter.check(makeReq("10.0.0.2"))).toBe(false);
  });
});

describe("createErrorResponse", () => {
  it("creates structured error", () => {
    const err = createErrorResponse(404, "Not found", "NOT_FOUND");
    expect(err.statusCode).toBe(404);
    expect(err.error).toBe("Not found");
    expect(err.code).toBe("NOT_FOUND");
    expect(err.requestId).toBeTruthy();
  });

  it("includes optional details", () => {
    const err = createErrorResponse(400, "Bad request", "INVALID", { field: "name" });
    expect(err.details).toEqual({ field: "name" });
  });
});

describe("RequestLogger", () => {
  it("logs requests", () => {
    const logger = new RequestLogger();
    logger.log({
      timestamp: new Date().toISOString(),
      method: "GET",
      path: "/health",
      statusCode: 200,
      durationMs: 5,
      ip: "127.0.0.1",
      userAgent: "test",
    });
    expect(logger.getRecent().length).toBe(1);
  });

  it("returns empty stats when no logs", () => {
    const logger = new RequestLogger();
    expect(logger.getStats()).toEqual({ total: 0, errors: 0, avgDuration: 0 });
  });

  it("computes stats correctly", () => {
    const logger = new RequestLogger();
    for (let i = 0; i < 10; i++) {
      logger.log({
        timestamp: new Date().toISOString(),
        method: "GET",
        path: "/health",
        statusCode: i < 2 ? 500 : 200,
        durationMs: i * 10,
        ip: "127.0.0.1",
        userAgent: "test",
      });
    }
    const stats = logger.getStats();
    expect(stats.total).toBe(10);
    expect(stats.errors).toBe(2);
    expect(stats.avgDuration).toBe(45); // (0+10+20+...+90)/10 = 45
  });

  it("respects max log limit", () => {
    const logger = new RequestLogger();
    for (let i = 0; i < 1500; i++) {
      logger.log({
        timestamp: new Date().toISOString(),
        method: "GET",
        path: "/test",
        statusCode: 200,
        durationMs: 1,
        ip: "127.0.0.1",
        userAgent: "test",
      });
    }
    // getRecent defaults to 50, pass explicit limit
    expect(logger.getRecent(500).length).toBe(500);
  });
});

describe("applyCORS", () => {
  it("sets CORS headers", () => {
    const res = makeRes();
    applyCORS(res);
    expect(res.getHeader("Access-Control-Allow-Origin")).toBe("*");
    expect(res.getHeader("Access-Control-Allow-Methods")).toBeTruthy();
    expect(res.getHeader("Access-Control-Allow-Headers")).toBeTruthy();
  });
});

describe("jsonResponse / jsonError", () => {
  it("jsonResponse sends JSON body", () => {
    const res = makeRes();
    // We can't easily test res.end in Node's ServerResponse,
    // but we can check the header
    jsonResponse(res, 200, { hello: "world" });
    expect(res.statusCode).toBe(200);
  });

  it("jsonError sets correct status", () => {
    const res = makeRes();
    jsonError(res, 429, "Too many", "RATE_LIMITED");
    expect(res.statusCode).toBe(429);
  });
});
