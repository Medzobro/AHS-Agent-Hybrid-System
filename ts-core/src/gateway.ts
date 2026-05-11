/**
 * AHS — Gateway Server (Middleware-enhanced)
 * ============================================
 * HTTP + WebSocket gateway for the AHS TypeScript Core.
 * Uses middleware: rate limiting, CORS, error handling, request logging.
 *
 * Endpoints:
 *   GET  /health     → System health status
 *   GET  /status     → Full AHS status
 *   POST /task       → Send a task (auto-classified)
 *   WS   /ws         → WebSocket for streaming
 *   GET  /logs       → Recent request logs
 *
 * Author: Aziz + Hermes
 */

import * as http from "http";
import * as os from "os";
import { type WebSocket, WebSocketServer } from "ws";
import type { AHEngine } from "./orchestrator/index.js";
import {
  RateLimiter,
  RequestLogger,
  applyCORS,
  jsonResponse,
  jsonError,
} from "./middleware.js";

export interface GatewayConfig {
  port: number;
  rateLimitWindowMs?: number;
  rateLimitMax?: number;
}

export interface GatewayStatus {
  running: boolean;
  port: number;
  connections: number;
  tasksProcessed: number;
  version: string;
  uptime: number;
  rateLimiter: {
    blocked: number;
  };
  requestLog: {
    total: number;
    errors: number;
    avgDuration: number;
  };
}

export class GatewayServer {
  private config: GatewayConfig;
  private server: http.Server | null = null;
  private wss: WebSocketServer | null = null;
  private engine: AHEngine;
  private connections: Set<WebSocket> = new Set();
  private tasksProcessed = 0;
  private startTime: number = Date.now();
  private rateLimiter: RateLimiter;
  private requestLogger: RequestLogger;

  constructor(config: GatewayConfig, engine: AHEngine) {
    this.config = config;
    this.engine = engine;
    this.rateLimiter = new RateLimiter({
      windowMs: config.rateLimitWindowMs ?? 60_000,
      maxRequests: config.rateLimitMax ?? 100,
    });
    this.requestLogger = new RequestLogger();
  }

  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = http.createServer((req, res) => this.handleRequest(req, res));

      // WebSocket server
      this.wss = new WebSocketServer({ server: this.server, path: "/ws" });
      this.wss.on("connection", (ws: WebSocket) => {
        this.connections.add(ws);
        console.log(`  🔗 WebSocket client connected (${this.connections.size} total)`);

        ws.on("message", async (data: Buffer | string) => {
          this.tasksProcessed++;
          try {
            const msg = JSON.parse(data.toString());
            const task = msg.task || msg.message || "";
            const result = await this.engine.process(task);
            ws.send(JSON.stringify(result));
          } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : String(err);
            ws.send(JSON.stringify({ success: false, error: errorMsg }));
          }
        });

        ws.on("close", () => {
          this.connections.delete(ws);
        });

        ws.on("error", (err: Error) => {
          console.error(`  ⚠️ WebSocket error: ${err.message}`);
          this.connections.delete(ws);
        });
      });

      this.server.listen(this.config.port, () => {
        resolve();
      });

      this.server.on("error", (err: Error) => {
        console.error(`  ❌ Gateway error: ${err.message}`);
        reject(err);
      });
    });
  }

  private async handleRequest(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    const startTime = Date.now();
    const url = new URL(req.url || "/", `http://${req.headers.host}`);

    // Apply CORS
    applyCORS(res);

    // Handle preflight
    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    // Rate limiting
    if (!this.rateLimiter.check(req)) {
      const elapsed = Date.now() - startTime;
      const stats = this.rateLimiter.getStats(req);
      this.requestLogger.log({
        timestamp: new Date().toISOString(),
        method: req.method || "UNKNOWN",
        path: url.pathname,
        statusCode: 429,
        durationMs: elapsed,
        ip: req.socket.remoteAddress || "unknown",
        userAgent: req.headers["user-agent"] || "",
      });

      res.writeHead(429, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          error: "Too many requests",
          code: "RATE_LIMITED",
          retryAfter: Math.ceil(stats.windowMs / 1000),
          statusCode: 429,
        }),
      );
      return;
    }

    try {
      await this.routeRequest(req, res, url);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      jsonError(res, 500, errorMsg, "INTERNAL_ERROR");
    } finally {
      const elapsed = Date.now() - startTime;
      const statusCode = res.statusCode || 200;
      this.requestLogger.log({
        timestamp: new Date().toISOString(),
        method: req.method || "UNKNOWN",
        path: url.pathname,
        statusCode,
        durationMs: elapsed,
        ip: req.socket.remoteAddress || "unknown",
        userAgent: req.headers["user-agent"] || "",
      });
    }
  }

  private async routeRequest(
    req: http.IncomingMessage,
    res: http.ServerResponse,
    url: URL,
  ): Promise<void> {
    switch (url.pathname) {
      case "/health":
        this.handleHealth(res);
        break;

      case "/status":
        this.handleStatus(res);
        break;

      case "/logs":
        this.handleLogs(res);
        break;

      case "/task":
        if (req.method !== "POST") {
          jsonError(res, 405, "Method not allowed", "METHOD_NOT_ALLOWED");
          return;
        }
        await this.handleTaskRequest(req, res);
        break;

      default:
        jsonError(res, 404, `Not found: ${url.pathname}`, "NOT_FOUND");
    }
  }

  private handleHealth(res: http.ServerResponse): void {
    jsonResponse(res, 200, {
      status: "ok",
      version: "0.4.0",
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      timestamp: new Date().toISOString(),
      connections: this.connections.size,
    });
  }

  private handleStatus(res: http.ServerResponse): void {
    jsonResponse(res, 200, {
      ...this.getStatus(),
      platform: os.platform(),
      hostname: os.hostname(),
      arch: os.arch(),
      cpus: os.cpus().length,
      memory: {
        free: os.freemem(),
        total: os.totalmem(),
        usagePercent: Math.round((1 - os.freemem() / os.totalmem()) * 100),
      },
      node: process.version,
    });
  }

  private handleLogs(res: http.ServerResponse): void {
    const limit = 50;
    jsonResponse(res, 200, {
      recent: this.requestLogger.getRecent(limit),
      stats: this.requestLogger.getStats(),
    });
  }

  private handleTaskRequest(req: http.IncomingMessage, res: http.ServerResponse): void {
    let body = "";
    req.on("data", (chunk: string) => (body += chunk));
    req.on("end", async () => {
      this.tasksProcessed++;
      try {
        const parsed = JSON.parse(body);
        const { task, mode } = parsed;

        if (!task) {
          jsonError(res, 400, 'Missing "task" field', "INVALID_REQUEST");
          return;
        }

        const result = await this.engine.process(task, mode || "auto");

        jsonResponse(res, 200, {
          ...result,
          gateway: "http",
        });
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        jsonError(res, 500, errorMsg, "TASK_ERROR");
      }
    });

    req.on("error", (err: Error) => {
      jsonError(res, 400, err.message, "INVALID_REQUEST_BODY");
    });
  }

  async stop(): Promise<void> {
    // Close all WebSocket connections
    for (const ws of this.connections) {
      try {
        ws.close();
      } catch {
        // ignore close errors
      }
    }
    this.connections.clear();

    // Close WebSocket server
    if (this.wss) {
      this.wss.close();
    }

    // Close HTTP server
    if (this.server) {
      return new Promise<void>((resolve) => {
        this.server!.close(() => resolve());
      });
    }
  }

  getStatus(): GatewayStatus {
    return {
      running: this.server !== null && this.server.listening,
      port: this.config.port,
      connections: this.connections.size,
      tasksProcessed: this.tasksProcessed,
      version: "0.4.0",
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
      rateLimiter: {
        blocked: 0,
      },
      requestLog: this.requestLogger.getStats(),
    };
  }
}
