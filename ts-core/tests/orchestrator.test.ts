// ============================================================
// AHS TypeScript Core — Orchestrator Tests
// ============================================================

import { describe, it, expect } from "vitest";
import { TaskClassifier, PlanBuilder, HybridOrchestrator } from "../src/orchestrator/index.js";

describe("TaskClassifier", () => {
  const classifier = new TaskClassifier();

  it("classifies greetings as openclaw/simple", () => {
    const result = classifier.classify("مرحبا");
    expect(result.agent).toBe("openclaw");
    expect(result.complexity).toBe("simple");
  });

  it("classifies hello as openclaw/simple", () => {
    const result = classifier.classify("hello");
    expect(result.agent).toBe("openclaw");
    expect(result.complexity).toBe("simple");
  });

  it("classifies research tasks as hermes/complex", () => {
    const result = classifier.classify("ابحث عن أفضل ممارسات AI Agents في 2026");
    expect(result.agent).toBe("hermes");
    expect(result.complexity).toMatch(/complex|research/);
  });

  it("classifies code tasks as hermes/medium+", () => {
    const result = classifier.classify("write a Python function to sort a list");
    expect(result.agent).toBe("hermes");
    expect(result.complexity).not.toBe("simple");
  });

  it("classifies long tasks as complex", () => {
    const long = "analyze ".repeat(100);
    const result = classifier.classify(long);
    expect(result.complexity).toBe("research");
    expect(result.confidence).toBeGreaterThanOrEqual(0.70);
  });
});

describe("PlanBuilder", () => {
  const classifier = new TaskClassifier();
  const builder = new PlanBuilder();

  it("builds 1 step for simple tasks", () => {
    const classification = classifier.classify("hi");
    const plan = builder.build("hi", classification);
    expect(plan.steps.length).toBe(1);
    expect(plan.steps[0]?.agent).toBe("openclaw");
  });

  it("builds 3+ steps for medium tasks", () => {
    const classification = classifier.classify("explain AI agents");
    const plan = builder.build("explain AI agents", classification);
    expect(plan.steps.length).toBeGreaterThanOrEqual(3);
  });

  it("builds 5+ steps for complex tasks", () => {
    const classification = classifier.classify("analyze the impact of large language models on software engineering practices");
    const plan = builder.build("analyze LLM impact", classification);
    expect(plan.steps.length).toBeGreaterThanOrEqual(5);
  });

  it("sets correct timeouts for each agent", () => {
    const classification = classifier.classify("write a Python script");
    const plan = builder.build("write a Python script", classification);

    for (const step of plan.steps) {
      if (step.agent === "hermes") {
        expect(step.timeout).toBeGreaterThanOrEqual(90_000);
      } else {
        expect(step.timeout).toBeLessThanOrEqual(30_000);
      }
    }
  });
});

describe("HybridOrchestrator", () => {
  const orchestrator = new HybridOrchestrator();

  it("processes a greeting", async () => {
    const result = await orchestrator.run("مرحبا");
    expect(result.success).toBe(true);
    expect(result.response).toContain("AHS");
    expect(result.elapsedMs).toBeGreaterThanOrEqual(0);
  });

  it("processes a research query", async () => {
    const result = await orchestrator.run("explain what an AI agent is");
    expect(result.success).toBe(true);
    expect(result.steps).toBeGreaterThanOrEqual(2);
  });

  it("processes a complex request", async () => {
    const result = await orchestrator.run(
      "research the best practices for building hybrid AI systems in 2026",
    );
    expect(result.success).toBe(true);
    expect(result.steps).toBeGreaterThanOrEqual(2);
  });

  it("logs all steps", async () => {
    const result = await orchestrator.run("hello world");
    expect(result.log.length).toBeGreaterThan(0);
    expect(result.log[0]?.agent).toBe("openclaw");
  });
});
