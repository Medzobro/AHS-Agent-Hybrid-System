// ============================================================
// AHS TypeScript Core — Middleware
// ============================================================
//
// Rate limiting, error handling, request logging, CORS.
// Plug into any HTTP server or gateway.
//
// Author: Aziz + Hermes

import type { IncomingMessage, ServerResponse } from "node:http";
import debug from "debug";

const log = debug("ahs:middleware");

// ─── Rate Limiter (Token Bucket) ─────────────────────────────

export interface RateLimiterConfig {
  windowMs: number; // time window in ms
  maxRequests: number; // max requests per window
  trustProxy: boolean; // use X-Forwarded-For
}

export interface RateLimiterStats {
  current: number;
  windowMs: number;
  maxRequests: number;
  remaining: number;
  resetTime: number;
  blocked: number;
}

export class RateLimiter {
  private config: RateLimiterConfig;
  private clients = new Map<string, { count: number; resetAt: number }>();
  private blockedCount = 0;

  constructor(config: Partial<RateLimiterConfig> = {}) {
    this.config = {
      windowMs: config.windowMs ?? 60_000,
      maxRequests: config.maxRequests ?? 100,
      trustProxy: config.trustProxy ?? false,
    };
  }

  /** Check if request is allowed. Returns true if allowed. */
  check(req: IncomingMessage): boolean {
    const now = Date.now();
    const key = this.getClientKey(req);

    let record = this.clients.get(key);

    // Window expired — reset
    if (!record || now >= record.resetAt) {
      record = { count: 0, resetAt: now + this.config.windowMs };
      this.clients.set(key, record);
    }

    record.count++;

    if (record.count > this.config.maxRequests) {
      this.blockedCount++;
      return false;
    }

    // Periodic cleanup (every 100 requests)
    if (this.clients.size > 10_000) {
      this.cleanup();
    }

    return true;
  }

  /** Get current stats for a client */
  getStats(req: IncomingMessage): RateLimiterStats {
    const key = this.getClientKey(req);
    const record = this.clients.get(key);
    const now = Date.now();

    return {
      current: record?.count ?? 0,
      windowMs: this.config.windowMs,
      maxRequests: this.config.maxRequests,
      remaining: record ? Math.max(0, this.config.maxRequests - record.count) : this.config.maxRequests,
      resetTime: record?.resetAt ?? now + this.config.windowMs,
      blocked: this.blockedCount,
    };
  }

  /** Reset all counters */
  reset(): void {
    this.clients.clear();
    this.blockedCount = 0;
  }

  private getClientKey(req: IncomingMessage): string {
    if (this.config.trustProxy) {
      const forwarded = req.headers["x-forwarded-for"];
      if (typeof forwarded === "string") return forwarded.split(",")[0].trim();
    }
    return req.socket?.remoteAddress ?? "unknown";
  }

  private cleanup(): void {
    const now = Date.now();
    for (const [key, record] of this.clients) {
      if (now >= record.resetAt) {
        this.clients.delete(key);
      }
    }
  }
}

// ─── Error Handler ──────────────────────────────────────────

export interface ErrorResponse {
  error: string;
  code: string;
  statusCode: number;
  details?: unknown;
  requestId?: string;
}

export function createErrorResponse(
  statusCode: number,
  error: string,
  code: string,
  details?: unknown,
): ErrorResponse {
  return {
    error,
    code,
    statusCode,
    details,
    requestId: generateRequestId(),
  };
}

function generateRequestId(): string {
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Request Logger ─────────────────────────────────────────

export interface LogEntry {
  timestamp: string;
  method: string;
  path: string;
  statusCode: number;
  durationMs: number;
  ip: string;
  userAgent: string;
}

export class RequestLogger {
  private logs: LogEntry[] = [];
  private maxLogs = 1000;

  log(entry: LogEntry): void {
    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
    log(`${entry.method} ${entry.path} → ${entry.statusCode} (${entry.durationMs}ms)`);
  }

  getRecent(limit = 50): LogEntry[] {
    return this.logs.slice(-limit);
  }

  getStats(): { total: number; errors: number; avgDuration: number } {
    if (this.logs.length === 0) return { total: 0, errors: 0, avgDuration: 0 };

    const errors = this.logs.filter((l) => l.statusCode >= 400).length;
    const avg = Math.round(this.logs.reduce((s, l) => s + l.durationMs, 0) / this.logs.length);

    return { total: this.logs.length, errors, avgDuration: avg };
  }
}

// ─── CORS Headers ───────────────────────────────────────────

export function applyCORS(res: ServerResponse): void {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-ID");
  res.setHeader("Access-Control-Max-Age", "86400");
}

// ─── JSON Response Helpers ──────────────────────────────────

export function jsonResponse(res: ServerResponse, statusCode: number, data: unknown): void {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

export function jsonError(
  res: ServerResponse,
  statusCode: number,
  error: string,
  code: string,
  details?: unknown,
): void {
  jsonResponse(res, statusCode, createErrorResponse(statusCode, error, code, details));
}
