// ============================================================
// AHS TypeScript Core — Agent Loop
// ============================================================
//
// The persistent execution loop that runs between gateway requests.
// Handles state, task scheduling, debouncing, and health pings.
//
// Author: Aziz + Hermes

import debug from "debug";
import { HermesBridge } from "./bridge/hermes-bridge.js";
import { AHEngine } from "./orchestrator/index.js";
import type { OrchestrationResult } from "./types/index.js";

const log = debug("ahs:agent-loop");

export interface AgentLoopConfig {
  heartbeatMs: number; // health ping interval (ms)
  maxQueueSize: number;
  idleTimeoutMs: number; // auto-stop after idle
  hermesEndpoint: string;
}

export interface AgentLoopStatus {
  running: boolean;
  uptime: number;
  tasksProcessed: number;
  tasksInQueue: number;
  lastTask: string;
  hermesConnected: boolean;
  healthStatus: "healthy" | "degraded" | "error";
}

export class AgentLoop {
  private config: AgentLoopConfig;
  private engine: AHEngine;
  private bridge: HermesBridge;
  private running = false;
  private startTime = 0;
  private tasksProcessed = 0;
  private lastTask = "none";
  private taskQueue: Array<{ task: string; mode: string }> = [];
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private processing = false;

  constructor(config: Partial<AgentLoopConfig> = {}) {
    this.config = {
      heartbeatMs: config.heartbeatMs ?? 30_000,
      maxQueueSize: config.maxQueueSize ?? 100,
      idleTimeoutMs: config.idleTimeoutMs ?? 300_000,
      hermesEndpoint: config.hermesEndpoint ?? "http://localhost:18900",
    };

    this.engine = new AHEngine();
    this.bridge = new HermesBridge({
      name: "hermes",
      transport: "http",
      endpoint: this.config.hermesEndpoint,
      tools: [],
    });
  }

  /** Start the agent loop */
  async start(): Promise<void> {
    if (this.running) return;

    this.startTime = Date.now();
    this.running = true;

    log("agent loop starting...");

    // Connect to Hermes
    try {
      await this.bridge.connect();
      log("✅ Hermes bridge connected");
    } catch (err) {
      log(`⚠️  Hermes bridge connection failed: ${err}`);
    }

    // Start heartbeat
    this.heartbeatTimer = setInterval(() => this.heartbeat(), this.config.heartbeatMs);
    log(`agent loop started (heartbeat: ${this.config.heartbeatMs}ms)`);
  }

  /** Process a task — adds to queue or processes immediately */
  async process(task: string, mode = "auto"): Promise<OrchestrationResult> {
    if (!this.running) {
      return {
        task,
        success: false,
        response: "Agent loop not running",
        steps: 0,
        elapsedMs: 0,
        log: [],
        error: "not_running",
      };
    }

    // Queue if busy
    if (this.processing) {
      if (this.taskQueue.length >= this.config.maxQueueSize) {
        return {
          task,
          success: false,
          response: "Queue full — try again later",
          steps: 0,
          elapsedMs: 0,
          log: [],
          error: "queue_full",
        };
      }

      this.taskQueue.push({ task, mode });
      return {
        task,
        success: true,
        response: "Queued",
        steps: 0,
        elapsedMs: 0,
        log: [],
      };
    }

    return this.executeTask(task, mode);
  }

  /** Execute a task immediately (bypasses queue) */
  async execute(task: string, mode = "auto"): Promise<OrchestrationResult> {
    return this.executeTask(task, mode);
  }

  private async executeTask(task: string, mode: string): Promise<OrchestrationResult> {
    this.processing = true;
    this.lastTask = task.slice(0, 60);
    this.tasksProcessed++;

    try {
      const result = await this.engine.process(task, mode);
      return result;
    } catch (err) {
      return {
        task,
        success: false,
        response: `Execution error: ${err instanceof Error ? err.message : String(err)}`,
        steps: 0,
        elapsedMs: 0,
        log: [],
        error: "execution_error",
      };
    } finally {
      this.processing = false;
      // Process next in queue
      if (this.taskQueue.length > 0) {
        const next = this.taskQueue.shift()!;
        setImmediate(() => this.executeTask(next.task, next.mode));
      }
    }
  }

  /** Heartbeat — health check and queue maintenance */
  private async heartbeat(): Promise<void> {
    if (!this.running) return;

    // Health check via Hermes
    try {
      const status = this.bridge.getStatus();
      if (this.heartbeatLog.length > 100) this.heartbeatLog.shift();
      this.heartbeatLog.push({
        time: Date.now(),
        hermesConnected: status.connected,
        queueSize: this.taskQueue.length,
        processing: this.processing,
      });
    } catch {
      log("heartbeat: hermes health check failed");
    }
  }

  /** Stop the agent loop */
  async stop(): Promise<void> {
    this.running = false;

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    await this.bridge.disconnect();
    log("agent loop stopped");
  }

  /** Get loop status */
  getStatus(): AgentLoopStatus {
    const uptime = this.startTime ? Math.floor((Date.now() - this.startTime) / 1000) : 0;
    const lastHb = this.heartbeatLog[this.heartbeatLog.length - 1];

    return {
      running: this.running,
      uptime,
      tasksProcessed: this.tasksProcessed,
      tasksInQueue: this.taskQueue.length,
      lastTask: this.lastTask,
      hermesConnected: lastHb?.hermesConnected ?? false,
      healthStatus: lastHb?.hermesConnected ? "healthy" : "degraded",
    };
  }

  get bridgeInstance(): HermesBridge {
    return this.bridge;
  }

  private heartbeatLog: Array<{
    time: number;
    hermesConnected: boolean;
    queueSize: number;
    processing: boolean;
  }> = [];
}
