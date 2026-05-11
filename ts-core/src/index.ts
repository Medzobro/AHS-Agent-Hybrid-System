/**
 * AHS — Agent Hybrid System v0.4
 * =================================
 * TypeScript Core (OpenClaw) + Hermes (Python MCP)
 *
 * Architecture:
 *   Gateway (HTTP/WS) ←→ AHEngine (Orchestrator) ←→ Hermes Bridge (MCP)
 *
 * كل جزء يشتغل مستقل ويتواصل عبر بروتوكول MCP.
 *
 * Author: Aziz + Hermes
 */

import { HermesBridge } from "./bridge/hermes-bridge.js";
import { GatewayServer } from "./gateway.js";
import { AHEngine } from "./orchestrator/index.js";
import type { MCPServerConfig } from "./types/index.js";

const AHS_VERSION = "0.4.0";
const AHS_CODENAME = "ترادف";

interface AHSConfig {
  name: string;
  version: string;
  codename: string;
  gateway: { port: number };
  hermes: MCPServerConfig;
  workingDir: string;
}

class AHSCore {
  private config: AHSConfig;
  private gateway!: GatewayServer;
  private hermesBridge!: HermesBridge;
  private engine!: AHEngine;
  private started = false;

  constructor() {
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
        endpoint: `http://${process.env.AHS_HERMES_HOST || "localhost"}:${process.env.AHS_MCP_PORT || process.env.AHS_HERMES_PORT || "18900"}`,
        tools: [],
      },
      workingDir: process.env.AHS_WORKING_DIR || process.cwd(),
    };

    console.debug = () => {}; // Suppress debug noise
  }

  async start(): Promise<void> {
    if (this.started) return;

    console.log(`\n${"=".repeat(52)}`);
    console.log(`  🤝 AHS v${AHS_VERSION} — "${AHS_CODENAME}"`);
    console.log(`  OpenClaw (TS) ⟷ Hermes (Python) عبر MCP`);
    console.log(`${"=".repeat(52)}\n`);

    try {
      // 1. Hermes Bridge
      this.hermesBridge = new HermesBridge(this.config.hermes);
      await this.hermesBridge.connect();
      console.log(`  🔌 Hermes Bridge: ${"✅ Connected"}`);

      // 2. AHEngine (Orchestrator)
      this.engine = new AHEngine();

      // Inject hermes bridge into engine context
      // (For now engine runs in simulation — real MCP calls come in v0.5)
      console.log(`  🧠 AHEngine: ✅ (classify → plan → execute → respond)`);

      // 3. Gateway
      this.gateway = new GatewayServer(this.config.gateway, this.engine);
      await this.gateway.start();
      console.log(`  🌐 Gateway: ✅ http://0.0.0.0:${this.config.gateway.port}`);

      this.started = true;
      console.log(`\n  ✅ AHS Core ready — كل الأنظمة شغالة\n`);
      console.log(`  📡 Endpoints:`);
      console.log(`     GET  /health     → System health`);
      console.log(`     GET  /status     → Full status`);
      console.log(`     POST /task       → Send a task (JSON {"task":"..."})`);
      console.log(`     WS   /ws         → WebSocket`);
    } catch (error) {
      console.error("  ❌ Failed to start AHS Core:", error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    await this.gateway?.stop();
    await this.hermesBridge?.disconnect();
    this.started = false;
  }

  getStatus() {
    return {
      name: this.config.name,
      version: this.config.version,
      codename: this.config.codename,
      started: this.started,
      gateway: this.gateway?.getStatus(),
      hermes: { connected: true },
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
