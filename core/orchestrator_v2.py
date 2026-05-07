#!/usr/bin/env python3
"""
AHS - Orchestrator V2
======================
Multi-step flow — OpenClaw and Hermes collaborate step by step.

Instead of "just ask Hermes", this orchestrator manages
a complete flow:
  OpenClaw → understands → plans → Hermes → thinks → OpenClaw → executes → responds
"""

import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bridge.hermes_bridge import HermesBridge
from typing import Dict, List, Optional


class HybridFlow:
    """
    Integrated hybrid flow between OpenClaw and Hermes.
    Each step is determined by the system based on task type.
    """

    def __init__(self):
        self.hermes = HermesBridge()
        self.steps_log: List[Dict] = []

    def run(self, task: str) -> Dict:
        """Run the complete hybrid flow"""
        self.steps_log = []
        start = time.time()

        task_lower = task.lower()

        # === Determine flow type ===
        if any(w in task_lower for w in ["كود", "برمج", "code", "python", "برنامج"]):
            flow_type = "code"
        elif any(w in task_lower for w in ["ابحث", "بحث", "what", "شرح", "معنى"]):
            flow_type = "research"
        else:
            flow_type = "general"

        # === OpenClaw: Step 1 — Understand task ===
        self._log("openclaw", "understand", f"Analysis: {flow_type}")

        # === OpenClaw: Step 2 — Plan ===
        plan = self._plan(flow_type, task)
        self._log("openclaw", "plan", f"Plan: {len(plan)} steps")

        # === Execution ===
        for i, step in enumerate(plan):
            actor = step["actor"]
            action = step["action"]

            if actor == "hermes":
                result = self._hermes_step(action, task)
            else:
                result = self._openclaw_step(action, task, step)

            self._log(actor, action, result[:100] if result else "Done")
            self.steps_log[-1]["full"] = result

        # === OpenClaw: Final step — Respond ===
        final = self._build_final_response()

        elapsed = time.time() - start

        return {
            "task": task,
            "flow_type": flow_type,
            "steps": len(self.steps_log),
            "elapsed": round(elapsed, 1),
            "final": final,
            "log": self.steps_log,
        }

    def _plan(self, flow_type: str, task: str) -> List[Dict]:
        """Plan steps based on task type"""
        if flow_type == "code":
            return [
                {"actor": "hermes", "action": "write_code", "prompt": f"Write Python code: {task}"},
            ]
        elif flow_type == "research":
            return [
                {"actor": "hermes", "action": "deep_think", "prompt": f"Analyze and explain: {task}"},
            ]
        else:
            return [
                {"actor": "hermes", "action": "answer", "prompt": f"Answer: {task}"},
            ]

    def _hermes_step(self, action: str, task: str) -> str:
        """Execute step via Hermes"""
        prompt = f"Think and answer accurately:\n{task}"
        result = self.hermes.send_task(
            task=prompt,
            skills="dogfood",
            thinking_mode=True,
            timeout=90
        )

        if result.get("success"):
            resp = result.get("response", {})
            content = resp.get("content", "") or resp.get("content_raw", "") or ""
            return content[:800]
        return f"[Hermes error: {result.get('error')}]"

    def _openclaw_step(self, action: str, task: str, step: Dict) -> str:
        """OpenClaw executes step"""
        if action == "understand":
            return "Task understood"
        elif action == "plan":
            return f"Planned {step.get('plan_type', 'general')}"
        elif action == "save":
            return "Saved"
        return "Done"

    def _build_final_response(self) -> str:
        """Build final response from all steps"""
        hermes_outputs = [
            s.get("full", "")
            for s in self.steps_log
            if s.get("actor") == "hermes" and s.get("full")
        ]

        if not hermes_outputs:
            return "🤝 **AHS** — Task completed"

        main = hermes_outputs[-1][:600]
        return f"🤝 **AHS Hybrid Agent**\n\n{main}"

    def _log(self, actor: str, action: str, result: str):
        self.steps_log.append({
            "actor": actor,
            "action": action,
            "result": result,
            "time": time.time(),
        })

    def show_log(self) -> str:
        """Display step log"""
        lines = []
        for s in self.steps_log:
            emoji = "🤖" if s["actor"] == "openclaw" else "🧠"
            lines.append(f"{emoji} {s['actor']} → {s['action']}: {s['result'][:80]}")
        return "\n".join(lines)


if __name__ == "__main__":
    flow = HybridFlow()
    r = flow.run("شرح الـ AI Agent بجملة")
    print(flow.show_log())
    print(f"\n{'-'*40}")
    print(f"⏱ {r['elapsed']}s | {r['steps']} steps")
    print(f"\n{r['final'][:300]}")