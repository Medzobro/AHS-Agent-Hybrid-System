/**
 * AHS — Agent Loop (TypeScript)
 * ==============================
 * The main loop: receive → classify → plan → execute → respond
 * 
 * Works with Hermes (Python) for deep thinking and tools.
 * Handles simple tasks directly in TypeScript.
 */

import { HermesBridgeClient } from './hermes-bridge.js';
import { AHSConfig } from './index.js';

export interface AgentLoopStatus {
  tasksProcessed: number;
  lastTask: string | null;
  hermesConnected: boolean;
}

interface TaskResult {
  task: string;
  mode: string;
  response: string;
  elapsed: number;
  steps: number;
}

type TaskMode = 'quick' | 'hybrid' | 'code' | 'deep' | 'auto';

export class AgentLoop {
  private config: AHSConfig;
  private hermesBridge: HermesBridgeClient;
  private tasksProcessed: number = 0;
  private lastTask: string | null = null;
  private history: TaskResult[] = [];

  constructor(config: AHSConfig, hermesBridge: HermesBridgeClient) {
    this.config = config;
    this.hermesBridge = hermesBridge;
  }

  /**
   * Main process function — called by Gateway.
   */
  async process(task: string, mode: string = 'auto'): Promise<TaskResult> {
    const start = Date.now();
    this.lastTask = task;

    const taskMode = this.classifyTask(task, mode);

    let response = '';
    let steps = 0;

    switch (taskMode) {
      case 'quick':
        response = this.processQuick(task);
        steps = 1;
        break;

      case 'deep':
        response = await this.processDeep(task);
        steps = 2;
        break;

      case 'code':
        response = await this.processCode(task);
        steps = 3;
        break;

      case 'hybrid':
      case 'auto':
      default:
        response = await this.processHybrid(task);
        steps = 3;
        break;
    }

    const elapsed = (Date.now() - start) / 1000;
    this.tasksProcessed++;

    const result: TaskResult = {
      task,
      mode: taskMode,
      response,
      elapsed,
      steps,
    };

    this.history.push(result);
    return result;
  }

  private classifyTask(task: string, preferredMode: string): TaskMode {
    if (preferredMode !== 'auto') {
      return preferredMode as TaskMode;
    }

    const lower = task.toLowerCase();
    if (lower.includes('code') || lower.includes('برمج') || lower.includes('كود') || lower.includes('python')) {
      return 'code';
    }
    if (lower.includes('بحث') || lower.includes('what') || lower.includes('why') || lower.includes('how') || lower.includes('ابحث')) {
      return 'deep';
    }
    if (lower.includes('hello') || lower.includes('hi') || lower.includes('تمام') || lower.includes('مرحبا') || lower.includes('من') && lower.includes('أنت')) {
      return 'quick';
    }
    if (task.length > 200) {
      return 'deep';
    }
    return 'hybrid';
  }

  private processQuick(task: string): string {
    const lower = task.toLowerCase();
    if (lower.includes('تمام') || lower.includes('جاهز')) {
      return 'جاهز تمام 🤝 AHS TypeScript Core!';
    }
    if (lower.includes('من أنت') || lower.includes('who are you')) {
      return `أنا **AHS (Agent Hybrid System)** v${this.config.version}\nنظام يجمع OpenClaw (TypeScript) + Hermes (Python)\nبواسطة MHamed 🤝`;
    }
    return `✅ تم الاستلام: "${task.slice(0, 50)}"`;
  }

  private async processDeep(task: string): Promise<string> {
    const result = await this.hermesBridge.sendTask(
      `Think deeply about this and provide a comprehensive answer:\n${task}`,
      60
    );

    if (result.success && result.response) {
      const content = (result.response as Record<string, unknown>).content as string || '';
      return `🧠 **Deep Analysis**\n\n${content.slice(0, 1000)}`;
    }

    return `⚠️ Hermes unavailable. Task: ${task.slice(0, 100)}`;
  }

  private async processCode(task: string): Promise<string> {
    const result = await this.hermesBridge.sendTask(
      `Write code for: ${task}\nProvide the complete code between <code> and </code>`,
      90
    );

    if (result.success && result.response) {
      const content = (result.response as Record<string, unknown>).content as string || '';
      return `💻 **Code**\n\n${content.slice(0, 1000)}`;
    }

    return `⚠️ Code generation unavailable. Task: ${task.slice(0, 100)}`;
  }

  private async processHybrid(task: string): Promise<string> {
    const result = await this.hermesBridge.sendTask(
      `Answer this question directly and helpfully:\n${task}`,
      90
    );

    if (result.success && result.response) {
      const content = (result.response as Record<string, unknown>).content as string || '';
      return `🤝 **AHS Hybrid Agent**\n\n${content.slice(0, 1000)}`;
    }

    return `⚠️ Hermes unavailable for hybrid mode. Try again later.`;
  }

  getStatus(): AgentLoopStatus {
    return {
      tasksProcessed: this.tasksProcessed,
      lastTask: this.lastTask,
      hermesConnected: this.hermesBridge.getStatus().connected,
    };
  }

  getHistory(limit: number = 5): TaskResult[] {
    return this.history.slice(-limit);
  }
}
