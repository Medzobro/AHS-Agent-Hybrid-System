/**
 * AHS — Gateway Server (Integrated)
 * ===================================
 * HTTP + WebSocket gateway for the AHS TypeScript Core.
 * Uses Hermes' HybridOrchestrator for intelligent routing.
 *
 * Endpoints:
 *   GET  /health     → System health status
 *   GET  /status     → Full AHS status
 *   POST /task       → Send a task (auto-classified)
 *   WS   /ws         → WebSocket for streaming
 */

import * as http from "http";
import * as os from "os";
import { type WebSocket, WebSocketServer } from "ws";
import type { AHEngine } from "./orchestrator/index.js";

export interface GatewayConfig {
  port: number;
}

export interface GatewayStatus {
  running: boolean;
  port: number;
  connections: number;
  tasksProcessed: number;
  version: string;
  uptime: number;
}

export class GatewayServer {
  private config: GatewayConfig;
  private server: http.Server | null = null;
  private wss: WebSocketServer | null = null;
  private engine: AHEngine;
  private connections: Set<WebSocket> = new Set();
  private tasksProcessed = 0;
  private startTime: number = Date.now();

  constructor(config: GatewayConfig, engine: AHEngine) {
    this.config = config;
    this.engine = engine;
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
      });

      this.server.listen(this.config.port, () => {
        resolve();
      });

      this.server.on("error", reject);
    });
  }

  private async handleRequest(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);

    // CORS
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    switch (url.pathname) {
      case "/health":
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "ok", version: "0.4.0" }));
        break;

      case "/status":
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            ...this.getStatus(),
            platform: os.platform(),
            hostname: os.hostname(),
          }),
        );
        break;

      case "/task":
        if (req.method !== "POST") {
          res.writeHead(405);
          res.end(JSON.stringify({ error: "Method not allowed" }));
          return;
        }
        await this.handleTaskRequest(req, res);
        break;

      default:
        res.writeHead(404);
        res.end(JSON.stringify({ error: "Not found", path: url.pathname }));
    }
  }

  private handleTaskRequest(req: http.IncomingMessage, res: http.ServerResponse): void {
    let body = "";
    req.on("data", (chunk: string) => (body += chunk));
    req.on("end", async () => {
      this.tasksProcessed++;
      try {
        const { task, mode } = JSON.parse(body);
        if (!task) {
          res.writeHead(400);
          res.end(JSON.stringify({ error: 'Missing "task" field' }));
          return;
        }

        const result = await this.engine.process(task, mode || "auto");

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            ...result,
            gateway: "http",
          }),
        );
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        res.writeHead(500);
        res.end(JSON.stringify({ error: errorMsg }));
      }
    });
  }

  async stop(): Promise<void> {
    // Close all WebSocket connections
    for (const ws of this.connections) {
      ws.close();
    }
    this.connections.clear();

    // Close WebSocket server
    if (this.wss) {
      this.wss.close();
    }

    // Close HTTP server
    if (this.server) {
      return new Promise((resolve) => {
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
    };
  }
}
