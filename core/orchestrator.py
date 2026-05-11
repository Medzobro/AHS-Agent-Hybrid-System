#!/usr/bin/env python3
"""
AHS - Agent Hybrid System
=========================
Central Core — Coordination between OpenClaw and Hermes

Principle: Each task is analyzed and then directed to the most suitable party.
- OpenClaw: Fast execution, commands, control
- Hermes: Deep thinking, research, multiple skills
"""

import json
import os
import time
from enum import Enum
from typing import Any


class TaskType(Enum):
    """Task types — who is suitable for them"""
    QUICK = "quick"           # Quick response → OpenClaw
    DEEP = "deep"             # Deep thinking → Hermes
    HYBRID = "hybrid"         # Both together
    SKILL = "skill"           # Specific skill → Hermes
    CODE = "code"             # Programming → OpenClaw + Hermes
    COMMAND = "command"       # Direct command → OpenClaw


class HybridOrchestrator:
    """
    The mastermind of the hybrid system.
    Decides who executes the task and follows up on results.
    """

    def __init__(self):
        self.memory_file = os.path.join(
            os.path.dirname(__file__), "../bridge/shared_memory.json"
        )
        self.history: list[dict] = []
        self.memory: dict = self._load_memory()

    def _load_memory(self) -> dict:
        """Load shared memory"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "learnings": [], "skills": []}

    def _save_memory(self):
        """Save shared memory"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def classify_task(self, task: str) -> tuple[TaskType, str]:
        """
        Analyze the task and determine its type and the appropriate party.
        """
        task_lower = task.lower()

        # Pattern detection
        patterns = {
            TaskType.QUICK: [
                "قل", "قول", "رد", "hello", "hi", "مرحبا", "شلونك",
                "كيفك", "تمام", "جاهز"
            ],
            TaskType.DEEP: [
                "حلل", "فكر", "ادرس", "ابحث", "learn", "analyze",
                "research", "deep", "معرفة", "science"
            ],
            TaskType.CODE: [
                "برمج", "اكتب كود", "code", "python", "function",
                "class", "برنامج", "تطبيق", "app"
            ],
            TaskType.COMMAND: [
                "نفذ", "شغل", "run", "execute", "افتح", "احذف",
                "انقل", "copy", "delete", "move"
            ],
        }

        for ttype, keywords in patterns.items():
            for kw in keywords:
                if kw in task_lower:
                    return ttype, f"classified_as_{ttype.value}"

        # Complex tasks → Hermes
        if len(task) > 200:
            return TaskType.HYBRID, "long_task"

        return TaskType.HYBRID, "default"

    def plan_execution(self, task: str, task_type: TaskType) -> dict:
        """
        Plan task execution — who does what.
        """
        plan = {
            "task": task,
            "type": task_type.value,
            "steps": [],
            "assignee": [],
        }

        if task_type == TaskType.QUICK:
            plan["steps"] = [{"action": "respond", "by": "openclaw"}]
            plan["assignee"] = ["openclaw"]

        elif task_type == TaskType.DEEP:
            plan["steps"] = [
                {"action": "analyze_task", "by": "openclaw"},
                {"action": "deep_think", "by": "hermes"},
                {"action": "summarize", "by": "openclaw"},
            ]
            plan["assignee"] = ["openclaw", "hermes"]

        elif task_type == TaskType.CODE:
            plan["steps"] = [
                {"action": "plan_code", "by": "openclaw"},
                {"action": "review_design", "by": "hermes"},
                {"action": "implement", "by": "openclaw"},
                {"action": "review_code", "by": "hermes"},
            ]
            plan["assignee"] = ["openclaw", "hermes"]

        elif task_type == TaskType.HYBRID:
            plan["steps"] = [
                {"action": "understand", "by": "openclaw"},
                {"action": "research", "by": "hermes"},
                {"action": "synthesize", "by": "openclaw"},
                {"action": "execute", "by": "openclaw"},
                {"action": "validate", "by": "hermes"},
            ]
            plan["assignee"] = ["openclaw", "hermes"]

        elif task_type == TaskType.COMMAND:
            plan["steps"] = [
                {"action": "validate_command", "by": "openclaw"},
                {"action": "execute", "by": "openclaw"},
            ]
            plan["assignee"] = ["openclaw"]

        return plan

    def record_learning(self, key: str, value: Any, source: str = "system"):
        """Record a new lesson in shared memory"""
        self.memory["learnings"].append({
            "key": key,
            "value": value,
            "source": source,
            "timestamp": time.time()
        })
        # Keep the last 100 lessons
        self.memory["learnings"] = self.memory["learnings"][-100:]
        self._save_memory()

    def get_relevant_learnings(self, task: str, limit: int = 5) -> list[dict]:
        """Retrieve lessons related to the task"""
        learnings = self.memory.get("learnings", [])
        task_lower = task.lower()
        relevant = []
        for l in learnings:
            key = l.get("key", "").lower()
            if any(word in key for word in task_lower.split()):
                relevant.append(l)
        return relevant[:limit]

    def run(self, task: str, user_id: str = "user") -> dict:
        """
        Run the task through the hybrid system.
        This function is called from OpenClaw when a command arrives.
        """
        # Record the task
        self.history.append({
            "user_id": user_id,
            "task": task,
            "timestamp": time.time(),
        })

        # Classification and planning
        task_type, reason = self.classify_task(task)
        plan = self.plan_execution(task, task_type)

        # Retrieve previous lessons
        context = self.get_relevant_learnings(task)

        result = {
            "task": task,
            "classification": {
                "type": task_type.value,
                "reason": reason,
            },
            "plan": plan,
            "context": context,
            "execution": [],
        }

        self._save_memory()
        return result


# Quick test
if __name__ == "__main__":
    orch = HybridOrchestrator()

    test_tasks = [
        "قل مرحبا",
        "ابحث عن أفضل طرق برمجة AI Agents",
        "اكتب كود Python لـ Agent بسيط",
        "حلل هذه المشكلة: نريد نظام هجين",
    ]

    for task in test_tasks:
        print(f"\n{'='*50}")
        print(f"📥 Task: {task}")
        result = orch.run(task)
        print(f"📊 Classification: {result['classification']['type']}")
        print("📋 Plan:")
        for step in result["plan"]["steps"]:
            print(f"   {step['action']} ← {step['by']}")