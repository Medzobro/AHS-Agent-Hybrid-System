// ============================================================
// AHS TypeScript Core — Hermes Bridge (MCP v6 Native)
// ============================================================
//
// Connects to Hermes Gateway via JSON-RPC 2.0 over MCP.
// Transport implementations: HTTP ✅ | stdio ⏳ | WebSocket ⏳
//
// Author: Aziz + Hermes

import { randomUUID } from "node:crypto";
import * as http from "node:http";
import * as https from "node:https";
import debug from "debug";
import type { BridgeMessage, BridgeResponse, MCPServerConfig, MCPTool, TransportType } from "../types/index.js";

const log = debug("ahs:bridge");

// ─── MCP Error ──────────────────────────────────────────────

export class MCPError extends Error {
  constructor(
    public readonly code: number,
    message: string,
    public readonly data?: unknown,
  ) {
    super(`MCP Error ${code}: ${message}`);
    this.name = "MCPError";
  }
}

// ─── MCP Session (Multi-Transport) ──────────────────────────

export class MCPSession {
  private config: MCPServerConfig;
  private active = false;
  private requestMap = new Map<
    string,
    {
      resolve: (value: unknown) => void;
      reject: (err: Error) => void;
      timer: NodeJS.Timeout;
    }
  >();
  private pendingBatch: Array<{ id: string; msg: BridgeMessage }> = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private batchInterval = 50; // ms

  constructor(config: MCPServerConfig) {
    this.config = config;
  }

  /** Initialize the connection */
  async connect(): Promise<void> {
    log(`connecting to ${this.config.name} via ${this.config.transport}`);

    if (this.config.transport === "http") {
      // Test connectivity via health endpoint (short timeout)
      const endpoint = this.config.endpoint || "http://localhost:18900";
      const healthUrl = endpoint.endsWith("/health") ? endpoint : `${endpoint.replace(/\/+$/, "")}/health`;

      try {
        await this.httpRequest("GET", healthUrl, undefined, 2000);
        log(`✅ HTTP transport connected: ${endpoint}`);
      } catch {
        log(`⚠️  HTTP health check failed (2s timeout) — will retry on first call`);
      }
    }

    this.active = true;
  }

  /** Send a JSON-RPC request and wait for response */
  async call(method: string, params: Record<string, unknown> = {}, timeout = 30_000): Promise<unknown> {
    if (!this.active) {
      throw new MCPError(-32000, "Session not connected");
    }

    const id = randomUUID();
    const msg: BridgeMessage = {
      jsonrpc: "2.0",
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.requestMap.delete(id);
        reject(new MCPError(-32001, `Request timed out after ${timeout}ms`));
      }, timeout);

      this.requestMap.set(id, { resolve, reject, timer });

      // Route to appropriate transport
      switch (this.config.transport) {
        case "http":
          this.sendHttp(msg, timeout);
          break;
        case "websocket":
          this.batch(msg);
          break;
        case "stdio":
          this.sendHttp(msg, timeout); // fallback to HTTP
          break;
        default:
          clearTimeout(timer);
          this.requestMap.delete(id);
          reject(new MCPError(-32002, `Unsupported transport: ${this.config.transport}`));
      }
    });
  }

  // ── HTTP Transport ──────────────────────────────────────────

  private async sendHttp(msg: BridgeMessage, _timeout: number): Promise<void> {
    try {
      const raw = JSON.stringify(msg);
      const endpoint = this.config.endpoint || "http://localhost:18900";
      const url = endpoint.endsWith("/mcp") ? endpoint : `${endpoint.replace(/\/+$/, "")}/mcp`;

      // Use a short HTTP timeout (3s) so failures are quick
      const response = await this.httpRequest("POST", url, raw, 3000);
      this.handleResponse(response);
    } catch (err) {
      const pending = this.requestMap.get(msg.id);
      if (pending) {
        clearTimeout(pending.timer);
        this.requestMap.delete(msg.id);
        pending.reject(err instanceof Error ? err : new Error(String(err)));
      }
    }
  }

  private httpRequest(
    method: string,
    url: string,
    body?: string,
    timeout = 30_000,
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const urlObj = new URL(url);
      const isHttps = urlObj.protocol === "https:";
      const transport = isHttps ? https : http;

      const options: http.RequestOptions = {
        hostname: urlObj.hostname,
        port: urlObj.port ? Number.parseInt(urlObj.port) : isHttps ? 443 : 80,
        path: urlObj.pathname + urlObj.search,
        method,
        headers: {
          "Content-Type": "application/json",
        },
        timeout,
      };

      if (body) {
        options.headers = {
          ...options.headers,
          "Content-Length": Buffer.byteLength(body),
        };
      }

      const req = transport.request(options, (res) => {
        let data = "";
        res.on("data", (chunk: string) => (data += chunk));
        res.on("end", () => resolve(data));
      });

      req.on("error", reject);
      req.on("timeout", () => {
        req.destroy();
        reject(new MCPError(-32001, `HTTP request timed out: ${method} ${url}`));
      });

      if (body) req.write(body);
      req.end();
    });
  }

  // ── Batching (for WebSocket transport) ──────────────────────

  private batch(msg: BridgeMessage): void {
    this.pendingBatch.push({ id: msg.id, msg });

    if (!this.batchTimer) {
      this.batchTimer = setTimeout(() => this.flushBatch(), this.batchInterval);
    }
  }

  private flushBatch(): void {
    this.batchTimer = null;
    if (this.pendingBatch.length === 0) return;

    const batch = this.pendingBatch.splice(0);
    // Flush batch via WebSocket (TODO: implement)
    log(`flushing ${batch.length} batched messages (WebSocket not yet implemented)`);

    for (const { id } of batch) {
      const pending = this.requestMap.get(id);
      if (pending) {
        clearTimeout(pending.timer);
        this.requestMap.delete(id);
        pending.reject(new MCPError(-32002, "WebSocket transport not implemented"));
      }
    }
  }

  // ── Response Handler ────────────────────────────────────────

  private handleResponse(raw: string): void {
    try {
      // Support batched responses (JSON array) or single
      const parsed = JSON.parse(raw);

      if (Array.isArray(parsed)) {
        for (const msg of parsed) {
          this.dispatchResponse(msg as BridgeResponse);
        }
      } else {
        this.dispatchResponse(parsed as BridgeResponse);
      }
    } catch (err) {
      log(`failed to parse response: ${err}`);
    }
  }

  private dispatchResponse(msg: BridgeResponse): void {
    const pending = this.requestMap.get(msg.id);
    if (!pending) {
      log(`unknown response id: ${msg.id.slice(0, 8)}...`);
      return;
    }

    clearTimeout(pending.timer);
    this.requestMap.delete(msg.id);

    if (msg.error) {
      pending.reject(new MCPError(msg.error.code, msg.error.message, msg.error.data));
    } else {
      pending.resolve(msg.result);
    }
  }

  // ── Lifecycle ──────────────────────────────────────────────

  async disconnect(): Promise<void> {
    this.active = false;

    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    // Reject all pending requests
    for (const [id, pending] of this.requestMap) {
      clearTimeout(pending.timer);
      pending.reject(new MCPError(-32003, "Session disconnected"));
    }
    this.requestMap.clear();
    this.pendingBatch = [];

    log(`disconnected from ${this.config.name}`);
  }

  get isActive(): boolean {
    return this.active;
  }
}

// ─── Hermes Bridge ────────────────────────────────────────────

export interface HermesTaskOptions {
  task: string;
  skills?: string[];
  timeout?: number;
  streaming?: boolean;
  context?: Record<string, unknown>;
}

export interface HermesTaskResult {
  success: boolean;
  content: string;
  reasoning?: string;
  toolCalls?: Array<{ name: string; args: Record<string, unknown> }>;
  elapsedMs: number;
  error?: string;
}

export interface HermesBridgeStatus {
  connected: boolean;
  transport: TransportType;
  endpoint: string;
  requestCount: number;
  errorCount: number;
  lastResponse: string;
  uptime: number;
}

export class HermesBridge {
  private session: MCPSession;
  private requestCount = 0;
  private errorCount = 0;
  private lastResponse = "never";
  private startTime = Date.now();

  constructor(config: MCPServerConfig) {
    this.session = new MCPSession(config);
  }

  /** Connect to Hermes MCP server */
  async connect(): Promise<void> {
    await this.session.connect();
  }

  /** Send a task to Hermes via MCP */
  async sendTask(options: HermesTaskOptions): Promise<HermesTaskResult> {
    const start = performance.now();
    this.requestCount++;

    try {
      const result = await this.session.call(
        "hermes/invoke",
        {
          task: options.task,
          skills: options.skills ?? [],
          context: options.context ?? {},
          stream: options.streaming ?? false,
        },
        options.timeout ?? 60_000,
      );

      const elapsed = performance.now() - start;
      this.lastResponse = "success";

      return {
        success: true,
        content: (result as { content: string })?.content ?? "",
        reasoning: (result as { reasoning?: string })?.reasoning,
        elapsedMs: Math.round(elapsed),
      };
    } catch (err) {
      const elapsed = performance.now() - start;
      this.errorCount++;
      this.lastResponse = "error";

      return {
        success: false,
        content: "",
        elapsedMs: Math.round(elapsed),
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  /** Send a simple prompt — blocks until response */
  async send(
    task: string,
    options: Partial<HermesTaskOptions> = {},
  ): Promise<HermesTaskResult> {
    return this.sendTask({
      task,
      ...options,
    });
  }

  /** List available MCP tools */
  async listTools(): Promise<MCPTool[]> {
    this.requestCount++;
    try {
      const result = await this.session.call("hermes/tools_list");
      this.lastResponse = "success";
      return (result as { tools: MCPTool[] })?.tools ?? [];
    } catch {
      this.errorCount++;
      this.lastResponse = "error";
      return [];
    }
  }

  /** Get bridge status */
  getStatus(): HermesBridgeStatus {
    return {
      connected: this.session.isActive,
      transport: "http",
      endpoint: "",
      requestCount: this.requestCount,
      errorCount: this.errorCount,
      lastResponse: this.lastResponse,
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
    };
  }

  /** Close the bridge */
  async disconnect(): Promise<void> {
    await this.session.disconnect();
  }
}
