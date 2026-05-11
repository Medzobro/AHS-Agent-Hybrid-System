// ============================================================
// AHS TypeScript Core — Hermes Bridge (MCP v6 Native)
// ============================================================
//
// Connects to Hermes Gateway via JSON-RPC 2.0 over MCP.
// No subprocess, no session file parsing — pure protocol.
// Supports: stdio, WebSocket, HTTP transports.

import { randomUUID } from "node:crypto";
import debug from "debug";
import type { BridgeMessage, BridgeResponse, MCPTool, MCPServerConfig, TransportType } from "../types/index.js";

const log = debug("ahs:bridge");

// ─── MCP Client ──────────────────────────────────────────────

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

export class MCPSession {
  private config: MCPServerConfig;
  private active = false;
  private requestMap = new Map<string, {
    resolve: (value: unknown) => void;
    reject: (err: Error) => void;
    timer: NodeJS.Timeout;
  }>();

  constructor(config: MCPServerConfig) {
    this.config = config;
  }

  /** Initialize the connection */
  async connect(): Promise<void> {
    log(`connecting to ${this.config.name} via ${this.config.transport}`);
    // TODO: implement transport initialization
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

      // TODO: send via transport (stdio / ws / http)
      log(`sending: ${method} (${id.slice(0, 8)}...)`);

      // For now, error if not implemented
      reject(new MCPError(-32002, "Transport not implemented — wire it up"));
    });
  }

  /** Handle an incoming response */
  private handleResponse(raw: string): void {
    try {
      const msg = JSON.parse(raw) as BridgeResponse;
      const pending = this.requestMap.get(msg.id);

      if (!pending) {
        log(`unknown response id: ${msg.id}`);
        return;
      }

      clearTimeout(pending.timer);
      this.requestMap.delete(msg.id);

      if (msg.error) {
        pending.reject(new MCPError(msg.error.code, msg.error.message, msg.error.data));
      } else {
        pending.resolve(msg.result);
      }
    } catch (err) {
      log(`failed to parse response: ${err}`);
    }
  }

  /** Close the connection */
  async disconnect(): Promise<void> {
    this.active = false;

    // Reject all pending requests
    for (const [id, pending] of this.requestMap) {
      clearTimeout(pending.timer);
      pending.reject(new MCPError(-32003, "Session disconnected"));
    }
    this.requestMap.clear();

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

export class HermesBridge {
  private session: MCPSession;

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

    try {
      const result = await this.session.call("hermes/invoke", {
        task: options.task,
        skills: options.skills ?? [],
        context: options.context ?? {},
        stream: options.streaming ?? false,
      }, options.timeout ?? 60_000);

      const elapsed = performance.now() - start;

      return {
        success: true,
        content: (result as { content: string }).content ?? "",
        reasoning: (result as { reasoning?: string }).reasoning,
        elapsedMs: Math.round(elapsed),
      };
    } catch (err) {
      const elapsed = performance.now() - start;

      return {
        success: false,
        content: "",
        elapsedMs: Math.round(elapsed),
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  /** List available MCP tools */
  async listTools(): Promise<MCPTool[]> {
    try {
      const result = await this.session.call("hermes/tools_list");
      return (result as { tools: MCPTool[] }).tools ?? [];
    } catch {
      return [];
    }
  }

  /** Close the bridge */
  async disconnect(): Promise<void> {
    await this.session.disconnect();
  }
}
