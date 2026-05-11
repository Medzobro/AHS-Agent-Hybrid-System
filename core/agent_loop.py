#!/usr/bin/env python3
"""
AHS - Agent Loop
=================
The main loop of the hybrid system.
Receives commands → classifies → plans → executes → responds.
"""

import os
import sys
import time

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.hermes_bridge import HermesBridge
from core.orchestrator import HybridOrchestrator
from skills.synthesizer import ResponseSynthesizer


class HybridAgent:
    """
    The main hybrid Agent.
    Combines OpenClaw + Hermes in a single loop.
    """

    def __init__(self):
        self.orchestrator = HybridOrchestrator()
        self.hermes = HermesBridge()
        self.history: list[dict] = []
        self.version = "0.1.0"
        self.name = "AHS (Agent Hybrid System)"

    def process(self, task: str, user_id: str = "user", hybrid: bool = False) -> dict:
        """
        Process a task through the hybrid system.

        1. Analyze the task
        2. Plan
        3. Execute plans (OpenClaw and/or Hermes)
        4. Compile the result
        5. Save to memory
        6. Respond

        Args:
            hybrid: If True → uses ResponseSynthesizer (OpenClaw + Hermes together)
        """
        start_time = time.time()

        # If hybrid → use the synthesizer
        if hybrid:
            synth = ResponseSynthesizer()
            result = synth.synthesize(task)
            self.orchestrator.record_learning(f"task_{len(self.history)}", {
                "task": task, "elapsed": result["elapsed"]
            })
            self.history.append(result)
            return {
                "task": task,
                "classification": "hybrid",
                "response": result["final"],
                "stats": {"elapsed_seconds": result["elapsed"], "hermes_used": True},
            }

        # Step 1-2: Analyze and plan
        classification = self.orchestrator.classify_task(task)
        plan = self.orchestrator.plan_execution(task, classification[0])

        # Step 3: Execution
        execution_log = []
        final_response = ""

        for step in plan["steps"]:
            action = step["action"]
            assignee = step["by"]

            step_result = self._execute_step(action, assignee, task, execution_log)
            execution_log.append({
                "step": action,
                "by": assignee,
                "result": step_result,
            })

            # If the last step is from OpenClaw and the previous from Hermes
            if assignee == "openclaw" and action in ["respond", "summarize", "synthesize"]:
                final_response = step_result or self._openclaw_respond(task, execution_log)

        # If we didn't get a final response
        if not final_response:
            # Use the synthesizer
            synth = ResponseSynthesizer()
            syn = synth.synthesize(task)
            final_response = syn["final"]

        # Step 5: Save to memory
        self.orchestrator.record_learning(
            key=f"task_{len(self.history)}",
            value={
                "task": task,
                "type": classification[0].value,
                "response_summary": final_response[:100],
            }
        )

        # Statistics
        elapsed = time.time() - start_time

        result = {
            "task": task,
            "classification": classification[0].value,
            "execution": execution_log,
            "response": final_response,
            "stats": {
                "elapsed_seconds": round(elapsed, 2),
                "steps": len(execution_log),
                "hermes_used": any(e["by"] == "hermes" for e in execution_log),
            }
        }

        # Save history
        self.history.append(result)

        return result

    def _execute_step(self, action: str, assignee: str, task: str, log: list) -> str | None:
        """Execute a single step of the plan"""
        try:
            if assignee == "hermes":
                return self._hermes_execute(action, task, log)
            elif assignee == "openclaw":
                return None  # OpenClaw handles the response directly
        except Exception as e:
            return f"⚠️ Execution error: {str(e)}"
        return None

    def _hermes_execute(self, action: str, task: str, log: list) -> str:
        """Execute a step via Hermes with thinking mode"""
        # Important: use a simple format that doesn't prompt Hermes to use unavailable tools
        hermes_task = (
            f"Think about this question and answer only:\n"
            f"Question: {task}\n\n"
            f"Provide a direct and helpful answer."
        )

        result = self.hermes.send_task(
            task=hermes_task,
            skills="dogfood",
            thinking_mode=True,
            timeout=60
        )

        if result.get("success"):
            response = result.get("response", {})
            content = response.get("content", "")
            reasoning = response.get("reasoning", "")
            if reasoning:
                return f"[Hermes Thinking]\n{reasoning[:300]}\n\n[Response]\n{content[:500]}"
            return content[:500]
        else:
            return f"⚠️ Hermes: {result.get('error', 'Unknown failure')}"

    def _openclaw_respond(self, task: str, log: list) -> str:
        """OpenClaw responds directly (me)"""
        # This function is called from OpenClaw itself
        # The response is written here as a last resort
        has_hermes = any(e.get("by") == "hermes" for e in log)
        hermes_outputs = [
            e["result"] for e in log
            if e.get("by") == "hermes" and e.get("result")
        ]

        if hermes_outputs:
            return f"🤝 **AHS Hybrid Agent**\n\n{hermes_outputs[-1]}"
        else:
            return self._direct_response(task)

    def _direct_response(self, task: str) -> str:
        """Direct response from OpenClaw for simple tasks"""
        task_lower = task.lower()

        greetings = ["مرحبا", "hello", "hi", "اهلا", "السلام"]
        for g in greetings:
            if g in task_lower:
                return "مرحباً! AHS Hybrid Agent جاهز 🚀"

        if "تمام" in task_lower or "جاهز" in task_lower:
            return "جاهز تمام 🤝"

        if "من" in task_lower or "who" in task_lower or "what" in task_lower:
            return (
                f"أنا **{self.name}** v{self.version}\n"
                f"نظام يجمع OpenClaw + Hermes\n"
                f"أفكر مع Hermes (DeepSeek R1) وأنفذ مع OpenClaw"
            )

        return "تم استلام المهمة. سأحللها مع Hermes وأعود لك بالنتيجة."

    def status(self) -> dict:
        """System status"""
        return {
            "name": self.name,
            "version": self.version,
            "tasks_processed": len(self.history),
            "hermes_connected": True,
            "model": "DeepSeek R1 (reasoner)",
            "last_task": self.history[-1] if self.history else None,
        }


# Test
if __name__ == "__main__":
    agent = HybridAgent()

    print(f"🤖 {agent.name} v{agent.version}")
    print("=" * 50)

    tests = [
        "من أنت",
        "تمام",
        "ابحث عن أفضل ممارسات AI Agents",
    ]

    for t in tests:
        print(f"\n📥: {t}")
        result = agent.process(t)
        print(f"📤: {result['response'][:200]}")
        print(f"⚡: {result['stats']}")
        print("-" * 30)