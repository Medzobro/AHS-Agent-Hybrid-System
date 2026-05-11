/**
 * AHS — Agent Hybrid System v1.0
 * ===============================
 * TypeScript Core (OpenClaw) + Hermes (Python MCP)
 *
 * Architecture:
 *   Gateway (HTTP/WS) ←→ AgentLoop ←→ AHEngine (Orchestrator) ←→ Hermes Bridge (MCP)
 *
 * كل جزء يشتغل مستقل ويتواصل عبر بروتوكول MCP.
 * v1.0: HTTP transport wired ✅ | Agent loop ✅ | Middleware ✅
 *
 * Author: Aziz + Hermes
 */

import { AgentLoop } from "./agent-loop.js";
import { GatewayServer } from "./gateway.js";
import type { MCPServerConfig } from "./types/index.js";

const AHS_VERSION = "1.0.0";
const AHS_CODENAME = "ترادف";

interface AHSConfig {
  name: string;
  version: string;
  codename: string;
  gateway: { port: number };
  hermes: MCPServerConfig;
  agentLoop: {
    heartbeatMs: number;
    maxQueueSize: number;
  };
  workingDir: string;
}

class AHSCore {
  private config: AHSConfig;
  private gateway!: GatewayServer;
  private agentLoop!: AgentLoop;
  private started = false;

  constructor() {
    const hermesHost = process.env.AHS_HERMES_HOST || "localhost";
    const hermesPort = process.env.AHS_MCP_PORT || process.env.AHS_HERMES_PORT || "18900";

    this.config = {
      name: "AHS-Agent-Hybrid-System",
      version: AHS_VERSION,
      codename: AHS_CODENAME,
      gateway: {
        port: Number.parseInt(process.env.AHS_GATEWAY_PORT || "18791"),
      },
      hermes: {
        name: "hermes",
        transport: "http",
        endpoint: `http://${hermesHost}:${hermesPort}`,
        tools: [],
      },
      agentLoop: {
        heartbeatMs: 30_000,
        maxQueueSize: 100,
      },
      workingDir: process.env.AHS_WORKING_DIR || process.cwd(),
    };

    // Suppress debug noise unless DEBUG env is set
    if (!process.env.DEBUG) {
      console.debug = () => {};
    }
  }

  async start(): Promise<void> {
    if (this.started) return;

    console.log(`\n${"=".repeat(52)}`);
    console.log(`  🤝 AHS v${AHS_VERSION} — "${AHS_CODENAME}"`);
    console.log(`  TypeScript Core + Hermes (Python MCP)`);
    console.log(`${"=".repeat(52)}\n`);

    try {
      // 1. Agent Loop (manages Hermes Bridge lifecycle)
      this.agentLoop = new AgentLoop({
        heartbeatMs: this.config.agentLoop.heartbeatMs,
        maxQueueSize: this.config.agentLoop.maxQueueSize,
        hermesEndpoint: this.config.hermes.endpoint!,
      });
      await this.agentLoop.start();
      const bridgeStatus = this.agentLoop.bridgeInstance.getStatus();
      console.log(`  🔌 Hermes Bridge: ${bridgeStatus.connected ? "✅ Connected" : "⚠️  Starting..."}`);

      // 2. AHEngine (via AgentLoop)
      console.log(`  🧠 AHEngine: ✅ (classify → plan → execute → respond)`);

      // 3. Gateway (uses AgentLoop for task processing)
      this.gateway = new GatewayServer(this.config.gateway, this.agentLoop as unknown as import("./orchestrator/index.js").AHEngine);
      await this.gateway.start();
      console.log(`  🌐 Gateway: ✅ http://0.0.0.0:${this.config.gateway.port}`);

      this.started = true;
      console.log(`\n  ✅ AHS Core v${AHS_VERSION} ready — كل الأنظمة شغالة\n`);
      console.log(`  📡 Endpoints:`);
      console.log(`     GET  /health     → System health`);
      console.log(`     GET  /status     → Full status`);
      console.log(`     GET  /logs       → Request logs`);
      console.log(`     POST /task       → Send a task (JSON {"task":"..."})`);
      console.log(`     WS   /ws         → WebSocket\n`);
    } catch (error) {
      console.error("  ❌ Failed to start AHS Core:", error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    await this.gateway?.stop();
    await this.agentLoop?.stop();
    this.started = false;
  }

  getStatus() {
    return {
      name: this.config.name,
      version: this.config.version,
      codename: this.config.codename,
      started: this.started,
      gateway: this.gateway?.getStatus(),
      agentLoop: this.agentLoop?.getStatus(),
    };
  }
}

// ——— CLI ———
const core = new AHSCore();

process.on("SIGINT", async () => {
  await core.stop();
  process.exit(0);
});
process.on("SIGTERM", async () => {
  await core.stop();
  process.exit(0);
});

core.start().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});

export { AHSCore, type AHSConfig };
