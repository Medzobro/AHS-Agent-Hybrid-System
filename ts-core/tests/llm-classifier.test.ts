// ============================================================
// AHS TypeScript Core — LLM Classifier Tests
// ============================================================

import { describe, it, expect, vi, beforeEach } from "vitest";
import { LLMClassifier, buildPlanWithLLM } from "../src/orchestrator/llm-classifier.js";
import { HermesBridge } from "../src/bridge/hermes-bridge.js";

const TEST_ENDPOINT = `http://localhost:${process.env.AHS_MCP_PORT || "1"}`;

describe("LLMClassifier (no Hermes — heuristic fallback)", () => {
  let classifier: LLMClassifier;

  beforeEach(() => {
    classifier = new LLMClassifier();
  });

  it("classifies greeting as openclaw simple", async () => {
    const result = await classifier.classify("مرحبا");
    expect(result.agent).toBe("openclaw");
    expect(result.complexity).toBe("simple");
    expect(result.confidence).toBeGreaterThanOrEqual(0);
  });

  it("classifies research as hermes complex", async () => {
    const result = await classifier.classify(
      "research the best AI frameworks for building autonomous agents in 2026",
    );
    expect(result.agent).toBe("hermes");
    expect(result.complexity).toBe("complex");
  });

  it("classifies code task as hermes medium", async () => {
    const result = await classifier.classify("write a Python script to parse JSON files");
    expect(result.agent).toBe("hermes");
    expect(result.complexity).toBe("medium");
  });

  it("tracks stats correctly", async () => {
    await classifier.classify("hello");
    await classifier.classify("research something");
    const stats = classifier.getStats();
    expect(stats.total).toBe(2);
    expect(stats.llmHits).toBe(0);
    expect(stats.fallbackHits).toBe(2);
  });
});

describe("LLMClassifier (with Hermes bridge — fails fast)", () => {
  let bridge: HermesBridge;
  let classifier: LLMClassifier;

  beforeEach(async () => {
    bridge = new HermesBridge({
      name: "hermes",
      transport: "http",
      endpoint: TEST_ENDPOINT,
      tools: [],
    });
    await bridge.connect();
    classifier = new LLMClassifier(bridge);
  });

  it("falls back to heuristic when Hermes is unavailable", async () => {
    const result = await classifier.classify("hello world");
    expect(result.agent).toBe("openclaw");
    expect(result.complexity).toBe("simple");
    // Should have tried LLM (failed) then fallen back
    const stats = classifier.getStats();
    expect(stats.fallbackHits).toBeGreaterThanOrEqual(1);
  });

  it("classifies research via fallback", async () => {
    const result = await classifier.classify("research quantum computing applications");
    expect(result.agent).toBe("hermes");
  });
});

describe("buildPlanWithLLM", () => {
  it("builds a plan for simple tasks", async () => {
    const classifier = new LLMClassifier();
    const plan = await buildPlanWithLLM("hello", classifier);
    expect(plan.steps.length).toBeGreaterThanOrEqual(1);
    expect(plan.steps[0].agent).toBe("openclaw");
    expect(plan.steps[0].timeout).toBeGreaterThan(0);
  });

  it("builds a plan for complex tasks", async () => {
    const classifier = new LLMClassifier();
    const plan = await buildPlanWithLLM(
      "research and explain the concept of decentralized AI",
      classifier,
    );
    expect(plan.steps.length).toBeGreaterThanOrEqual(3);
    expect(plan.steps.some((s) => s.agent === "hermes")).toBe(true);
  });
});
