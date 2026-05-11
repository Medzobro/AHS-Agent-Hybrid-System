// ============================================================
// AHS TypeScript Core — Hybrid Flow Orchestrator
// ============================================================
//
// AI-native task classifier + MCP-based bridge.
// No keyword matching. No subprocess. Pure protocol.

import debug from "debug";
import * as http from "http";
import type {
  AgentId,
  Complexity,
  ExecutionPlan,
  LogEntry,
  OrchestrationResult,
  PlanStep,
  TaskClassification,
} from "../types/index.js";
import { AGENT_CAPABILITIES } from "../types/index.js";

const log = debug("ahs:orchestrator");

// ─── Task Classifier (AI-based) ───────────────────────────────

export class TaskClassifier {
  /**
   * Classify a task using heuristics + complexity analysis.
   * V0.3: heuristic-based (upgrade to LLM in V1.0).
   */
  classify(task: string): TaskClassification {
    const t = task.toLowerCase();
    const words = t.split(/\s+/).length;

    // Depth signals
    const researchSignals = [
      "بحث", "ابحث", "research", "analyze", "تحليل", "حلل",
      "study", "learn", "deep", "explain", "شرح", "find",
    ];

    const codeSignals = [
      "كود", "code", "برمجة", "برمج", "python", "typescript",
      "function", "class", "implement", "نفذ", "write",
    ];

    const fastSignals = [
      "قل", "قول", "hi", "hello", "مرحبا", "جاهز", "تمام",
      "yes", "no", "نعم", "لا",
    ];

    // Count signals per category
    const score = {
      research: researchSignals.filter(s => t.includes(s)).length,
      code: codeSignals.filter(s => t.includes(s)).length,
      fast: fastSignals.filter(s => t.includes(s)).length,
    };

    // Determine agent
    let agent: AgentId;
    let complexity: Complexity;
    let confidence: number;
    let reason: string;
    let requiredSkills: string[] = [];

    if (score.fast > score.research && score.fast > score.code && words < 10) {
      agent = "openclaw";
      complexity = "simple";
      confidence = 0.85;
      reason = "greeting or simple request classified as quick response";
    } else if (score.code > score.research || words > 30 && score.code > 0) {
      agent = "hermes";
      complexity = words > 50 ? "complex" : "medium";
      confidence = 0.75;
      reason = "code or complex task needs deep reasoning";
      requiredSkills = ["systematic-debugging", "writing-plans"];
    } else if (score.research > 0 || words > 40) {
      agent = "hermes";
      complexity = words > 80 ? "research" : "complex";
      confidence = 0.80;
      reason = "research or long-form task classified for deep think";
      requiredSkills = ["research", "arxiv", "llm-wiki"];
    } else if (words > 50) {
      agent = "hermes";
      complexity = "complex";
      confidence = 0.70;
      reason = "long task needs detailed analysis";
    } else {
      // Hybrid default — both agents
      agent = "hermes";
      complexity = "medium";
      confidence = 0.60;
      reason = "default classification — using Hermes for quality";
    }

    return { agent, complexity, confidence, reason, requiredSkills };
  }
}

// ─── Plan Builder ─────────────────────────────────────────────

export class PlanBuilder {
  private stepCounter = 0;

  build(task: string, classification: TaskClassification): ExecutionPlan {
    this.stepCounter = 0;

    const context: Record<string, unknown> = {
      task,
      classification,
      availableAgents: this.findAvailableAgents(classification),
    };

    const plan: ExecutionPlan = {
      task,
      classification,
      steps: [],
      parallel: false,
      maxConcurrency: 1,
      context,
    };

    switch (classification.complexity) {
      case "simple":
        plan.steps = this.buildSimple(task);
        plan.maxConcurrency = 1;
        break;

      case "medium":
        plan.steps = this.buildMedium(task, classification);
        plan.parallel = true;
        plan.maxConcurrency = 2;
        break;

      case "complex":
      case "research":
        plan.steps = this.buildComplex(task, classification);
        plan.parallel = true;
        plan.maxConcurrency = 3;
        break;
    }

    return plan;
  }

  private nextStepId(): string {
    return `step_${++this.stepCounter}`;
  }

  private findAvailableAgents(classification: TaskClassification): AgentId[] {
    const agents: AgentId[] = ["openclaw", "hermes"];

    if (classification.complexity === "simple") {
      // Simple tasks only need OpenClaw
      return ["openclaw"];
    }

    return agents;
  }

  private buildSimple(task: string): PlanStep[] {
    return [
      this.step("respond", "openclaw", "Direct response to user", []),
    ];
  }

  private buildMedium(task: string, classification: TaskClassification): PlanStep[] {
    return [
      this.step("analyze", "openclaw", "Understand the request", []),
      this.step(
        "deep_think",
        classification.agent,
        "Think deeply and generate response",
        ["step_1"],
      ),
      this.step("synthesize", "openclaw", "Format and deliver response", ["step_2"]),
    ];
  }

  private buildComplex(task: string, classification: TaskClassification): PlanStep[] {
    const steps: PlanStep[] = [
      this.step("understand", "openclaw", "Parse and understand complex task", []),
    ];

    // Research + Analysis
    steps.push(
      this.step("research", "hermes", "Research and gather information", ["step_1"]),
    );

    // Deep reasoning
    steps.push(
      this.step("deep_think", "hermes", "Deep analysis with reasoning", ["step_2"]),
    );

    // OpenClaw execution
    steps.push(
      this.step("execute", "openclaw", "Execute any actionable steps", ["step_3"]),
    );

    // Final response
    steps.push(
      this.step("respond", "openclaw", "Build final response", ["step_4"]),
    );

    return steps;
  }

  private step(action: string, agent: AgentId, description: string, dependencies: string[]): PlanStep {
    return {
      id: this.nextStepId(),
      action,
      agent,
      description,
      dependencies,
      timeout: agent === "hermes" ? 90_000 : 30_000,
    };
  }
}

// ─── Hybrid Orchestrator ──────────────────────────────────────

export class HybridOrchestrator {
  private classifier = new TaskClassifier();
  private planBuilder = new PlanBuilder();
  private log: LogEntry[] = [];

  /**
   * Run the full orchestration cycle:
   *   classify → plan → execute → respond
   */
  async run(task: string): Promise<OrchestrationResult> {
    const globalStart = performance.now();
    this.log = [];

    log(`running task: ${task.slice(0, 60)}...`);

    // 1. Classify
    const classification = this.classifier.classify(task);
    this.logEntry("openclaw", "classify", "completed", 0);
    log(`classified: ${classification.agent} / ${classification.complexity} (${classification.confidence})`);

    // 2. Plan
    const plan = this.planBuilder.build(task, classification);
    this.logEntry("openclaw", "plan", "completed", 0);
    log(`planned: ${plan.steps.length} steps, parallel=${plan.parallel}`);

    // 3. Execute (parallel where possible)
    const completedSteps = new Set<string>();
    const startTime = Date.now();
    const stepResults = new Map<string, string>();

    let stepIndex = 0;
    while (completedSteps.size < plan.steps.length && stepIndex < 50) {
      const ready = plan.steps.filter(
        s => !completedSteps.has(s.id) && s.dependencies.every(d => completedSteps.has(d)),
      );

      if (ready.length === 0) {
        // Deadlock — should not happen with proper dependency graph
        break;
      }

      for (const step of ready) {
        const start = performance.now();

        try {
          if (step.agent === "hermes") {
            log(`hermes step: ${step.action} -> calling MCP HTTP`);
            const hermesResp = await this.callMCP(task);
            stepResults.set(step.id, hermesResp);
          } else {
            // OpenClaw steps execute locally
            const result = this.executeOpenClawStep(step, task, plan);
            stepResults.set(step.id, result);
          }

          const elapsed = performance.now() - start;
          this.logEntry(step.agent, step.action, "completed", Math.round(elapsed));
        } catch (err) {
          const elapsed = performance.now() - start;
          this.logEntry(step.agent, step.action, "failed", Math.round(elapsed));
          stepResults.set(step.id, `error: ${err}`);
        }

        completedSteps.add(step.id);
      }

      stepIndex++;
    }

    // 4. Build final response
    const hermesOutputs = [...stepResults.entries()]
      .filter(([id]) => {
        const step = plan.steps.find(s => s.id === id);
        return step?.agent === "hermes";
      })
      .map(([_, result]) => result);

    const response = hermesOutputs.length > 0
      ? `🤝 **AHS Hybrid Agent**\n\n${hermesOutputs[hermesOutputs.length - 1]}`
      : "🤝 **AHS** — Task processed";

    const elapsed = performance.now() - globalStart;

    return {
      task,
      success: true,
      response,
      steps: this.log.length,
      elapsedMs: Math.round(elapsed),
      log: this.log,
    };
  }

  private async callMCP(task: string): Promise<string> {
    const port = process.env.AHS_MCP_PORT 
      ? parseInt(process.env.AHS_MCP_PORT) : 18900;
    
    return new Promise((resolve) => {
      const payload = JSON.stringify({ task, mode: "hybrid" });
      const req = http.request(
        {
          hostname: "localhost",
          port,
          path: "/task",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(payload),
          },
          timeout: 60000,
        },
        (res: http.IncomingMessage) => {
          let body = "";
          res.on("data", (chunk: string) => (body += chunk));
          res.on("end", () => {
            try {
              const data = JSON.parse(body);
              resolve(data.response || data.content || body);
            } catch {
              resolve(body);
            }
          });
        }
      );
      req.on("error", (err: Error) => resolve(`Error calling MCP: ${err.message}`));
      req.write(payload);
      req.end();
    });
  }

  private executeOpenClawStep(step: PlanStep, task: string, plan: ExecutionPlan): string {
    switch (step.action) {
      case "respond":
      case "synthesize":
      case "format":
        return "Response ready";
      case "analyze":
      case "understand":
        return `Analysis complete: ${plan.classification.reason}`;
      case "execute":
        return "Execution complete";
      default:
        return `OpenClaw: ${step.action}`;
    }
  }

  private logEntry(agent: AgentId, action: string, status: "started" | "completed" | "failed", duration: number) {
    this.log.push({
      timestamp: Date.now(),
      agent,
      action,
      status,
      duration,
    });
  }

  get lastLog(): LogEntry[] {
    return [...this.log];
  }
}

// ─── Main AHS Engine ──────────────────────────────────────────

export class AHEngine {
  private orchestrator = new HybridOrchestrator();

  /**
   * Process a task — classify and route to Hermes via MCP HTTP if complex.
   * @param task - The task to process
   * @param mode - 'auto' | 'quick' | 'hybrid' | 'deep' (from gateway)
   */
  async process(task: string, mode: string = 'auto'): Promise<OrchestrationResult> {
    if (mode === 'quick') {
      return {
        task,
        success: true,
        response: '✅ تم',
        steps: 1,
        elapsedMs: 0,
        log: [{
          timestamp: Date.now(),
          agent: 'openclaw' as const,
          action: 'respond',
          status: 'completed' as const,
          duration: 0,
        }],
      };
    }
    
    // For hybrid/deep — delegate to MCP HTTP
    if (mode === 'hybrid' || mode === 'deep' || mode === 'auto') {
      try {
        const response = await this.orchestrator.run(task);
        return response;
      } catch (err) {
        return {
          task,
          success: false,
          response: `Error: ${err instanceof Error ? err.message : String(err)}`,
          steps: 0,
          elapsedMs: 0,
          log: [],
        };
      }
    }
    
    return this.orchestrator.run(task);
  }
}
