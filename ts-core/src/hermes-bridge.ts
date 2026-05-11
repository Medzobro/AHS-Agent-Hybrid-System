/**
 * AHS — Hermes Bridge Client (TypeScript → Python MCP)
 * ======================================================
 * Connects OpenClaw (TS Core) to Hermes (Python MCP Server).
 * 
 * Protocol: WebSocket to Python MCP server on configured port.
 * Fallback: HTTP REST API call to Python bridge.
 */

import WebSocket from 'ws';
import * as http from 'http';

interface HermesConfig {
  host: string;
  port: number;
}

export interface BridgeStatus {
  connected: boolean;
  host: string;
  port: number;
  lastPing?: number;
  lastResponse?: string;
}

interface BridgeResponse {
  success: boolean;
  method: string;
  response?: Record<string, unknown>;
  error?: string;
}

export class HermesBridgeClient {
  private config: HermesConfig;
  private ws: WebSocket | null = null;
  private status: BridgeStatus;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(config: HermesConfig) {
    this.config = config;
    this.status = {
      connected: false,
      host: config.host,
      port: config.port,
    };
  }

  async connect(): Promise<void> {
    // Try WebSocket first, then HTTP
    try {
      await this.connectWebSocket();
    } catch {
      console.log('  ⚠️ WebSocket failed, trying HTTP...');
      try {
        await this.checkHttpBridge();
        console.log('  ✅ HTTP bridge available');
      } catch {
        console.log('  ⚠️ No bridge server running — will use CLI fallback');
        this.status.connected = false;
      }
    }
  }

  private async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = `ws://${this.config.host}:${this.config.port}`;
      const ws = new WebSocket(url);

      ws.on('open', () => {
        this.ws = ws;
        this.status.connected = true;
        console.log(`  🔗 WebSocket connected to ${url}`);
        resolve();
      });

      ws.on('close', () => {
        this.status.connected = false;
        this.scheduleReconnect();
      });

      ws.on('error', (err) => {
        reject(err);
      });

      ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data.toString());
          this.status.lastResponse = JSON.stringify(msg).slice(0, 100);
        } catch {
          this.status.lastResponse = data.toString().slice(0, 100);
        }
      });

      // Timeout
      setTimeout(() => {
        if (!this.status.connected) {
          ws.close();
          reject(new Error('WebSocket connection timeout'));
        }
      }, 5000);
    });
  }

  private async checkHttpBridge(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = http.get(
        `http://${this.config.host}:${this.config.port}/health`,
        (res) => {
          this.status.connected = res.statusCode === 200;
          resolve();
        }
      );
      req.on('error', reject);
      req.setTimeout(3000, () => {
        req.destroy();
        reject(new Error('HTTP health check timeout'));
      });
    });
  }

  /**
   * Send a task to Hermes via available method.
   */
  async sendTask(task: string, timeoutSec: number = 30): Promise<BridgeResponse> {
    // 1. Try WebSocket
    if (this.ws && this.status.connected) {
      try {
        return await this.sendViaWebSocket(task, timeoutSec);
      } catch {
        // Fall through
      }
    }

    // 2. Try HTTP
    try {
      return await this.sendViaHttp(task, timeoutSec);
    } catch {
      // Fall through
    }

    return { success: false, method: 'none', error: 'No Hermes connection available' };
  }

  private async sendViaWebSocket(task: string, timeoutSec: number): Promise<BridgeResponse> {
    return new Promise((resolve, reject) => {
      if (!this.ws) {
        return reject(new Error('WebSocket not connected'));
      }

      const timer = setTimeout(() => {
        reject(new Error(`WebSocket response timeout (${timeoutSec}s)`));
      }, timeoutSec * 1000);

      const handler = (data: WebSocket.Data) => {
        clearTimeout(timer);
        this.ws?.off('message', handler);
        resolve({
          success: true,
          method: 'websocket',
          response: { content: data.toString() },
        });
      };

      this.ws.on('message', handler);
      this.ws.send(JSON.stringify({ type: 'task', payload: task }));
    });
  }

  private async sendViaHttp(task: string, timeoutSec: number): Promise<BridgeResponse> {
    return new Promise((resolve, reject) => {
      const payload = JSON.stringify({ task });
      const req = http.request(
        {
          hostname: this.config.host,
          port: this.config.port,
          path: '/task',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(payload),
          },
          timeout: timeoutSec * 1000,
        },
        (res) => {
          let body = '';
          res.on('data', (chunk) => (body += chunk));
          res.on('end', () => {
            try {
              resolve({
                success: true,
                method: 'http',
                response: JSON.parse(body),
              });
            } catch {
              resolve({
                success: true,
                method: 'http',
                response: { content: body },
              });
            }
          });
        }
      );

      req.on('error', reject);
      req.write(payload);
      req.end();
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      try {
        await this.connect();
      } catch {
        this.scheduleReconnect();
      }
    }, 5000);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.status.connected = false;
  }

  getStatus(): BridgeStatus {
    return { ...this.status };
  }
}
