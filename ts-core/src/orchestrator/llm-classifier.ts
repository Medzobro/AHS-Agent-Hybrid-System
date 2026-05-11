// ============================================================
// AHS TypeScript Core — LLM Task Classifier
// ============================================================
// Upgraded classifier: uses Hermes LLM for classification,
// falls back to heuristic when Hermes is unavailable.

import { HermesBridge } from "../bridge/hermes-bridge.js";
import {
  TaskComplexity,
  ExecutionPlan,
} from "../types/index.js";
import { TaskClassifier, PlanBuilder } from "./index.js";

export interface ClassificationResult {
  agent: "openclaw" | "hermes";
  complexity: TaskComplexity;
  confidence: number;
}

const CLASSIFICATION_PROMPT = `You are an AI task classifier for the AHS (Agent Hybrid System).
Your job: classify a user request into:
- Agent: "openclaw" (simple, direct, non-research) or "hermes" (research, coding, complex)
- Complexity: "simple", "medium", "complex", or "critical"
- Confidence: 0.0–1.0 (how sure you are)

Respond with ONLY a JSON object:
{"agent":"...","complexity":"...","confidence":0.0}`;

/**
 * LLM-powered task classifier with heuristic fallback.
 * Uses HermesBridge to send classification prompts to Hermes LLM.
 */
export class LLMClassifier {
  private bridge: HermesBridge | null = null;
  private fallbackHits = 0;
  private llmHits = 0;
  private heuristicClassifier: TaskClassifier;

  constructor(bridge?: HermesBridge) {
    this.bridge = bridge ?? null;
    this.heuristicClassifier = new TaskClassifier();
  }

  /** Set or replace the bridge instance */
  setBridge(bridge: HermesBridge): void {
    this.bridge = bridge;
  }

  /** Stats for monitoring */
  getStats(): { llmHits: number; fallbackHits: number; total: number } {
    return {
      llmHits: this.llmHits,
      fallbackHits: this.fallbackHits,
      total: this.llmHits + this.fallbackHits,
    };
  }

  /**
   * Classify a task using LLM (via Hermes) with heuristic fallback.
   */
  async classify(task: string): Promise<ClassificationResult> {
    // Try LLM first
    if (this.bridge && this.bridge.getStatus().connected) {
      try {
        const result = await this.tryLLMClassify(task);
        if (result) {
          this.llmHits++;
          return result;
        }
      } catch {
        // LLM failed, fall through to heuristic
      }
    }

    // Heuristic fallback
    this.fallbackHits++;
    return this.heuristicFallback(task);
  }

  /**
   * Use LLM to classify. Returns null if Hermes is unavailable or response is invalid.
   */
  private async tryLLMClassify(task: string): Promise<ClassificationResult | null> {
    if (!this.bridge) return null;

    const prompt = `${CLASSIFICATION_PROMPT}\n\nTask: "${task}"`;
    const response = await this.bridge.send(prompt);

    if (!response.success || !response.content) return null;

    try {
      const parsed = JSON.parse(response.content);
      const agent = parsed.agent === "hermes" ? "hermes" : "openclaw";
      const complexity = this.normalizeComplexity(parsed.complexity);
      const confidence = typeof parsed.confidence === "number" ? parsed.confidence : 0.5;

      return { agent, complexity, confidence };
    } catch {
      return null;
    }
  }

  private normalizeComplexity(c: string): TaskComplexity {
    switch (c?.toLowerCase()) {
      case "simple":
        return "simple";
      case "medium":
        return "medium";
      case "complex":
        return "complex";
      case "critical":
        return "critical";
      default:
        return "simple";
    }
  }

  private heuristicFallback(task: string): ClassificationResult {
    const heuristic = this.heuristicClassifier.classify(task);
    return {
      agent: heuristic.agent === "hermes" ? "hermes" : "openclaw",
      complexity: heuristic.complexity,
      confidence: 0.7,
    };
  }
}

/**
 * Build an execution plan using LLM-enhanced classification.
 * Delegates plan structure to PlanBuilder, but uses LLM for agent/complexity.
 */
export async function buildPlanWithLLM(
  task: string,
  classifier: LLMClassifier,
): Promise<ExecutionPlan> {
  const classification = await classifier.classify(task);
  const planBuilder = new PlanBuilder();
  const classification2: import("../types/index.js").TaskClassification = {
    agent: classification.agent,
    complexity: classification.complexity,
  };
  const plan = planBuilder.build(task, classification2);

  // Tag the plan with LLM confidence
  return {
    ...plan,
    steps: plan.steps.map((step) => ({
      ...step,
      agent: step.agent === "hermes" && classification.agent === "openclaw"
        ? "openclaw"
        : step.agent,
    })),
  };
}
