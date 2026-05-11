#!/usr/bin/env python3
"""
AHS - Integration Layer
=========================
Connects all AHS components (cleaned — no dead modules).
"""

import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import system.self_learn as sl
from bridge.hermes_bridge import HermesBridge
from system.skill_manager import SkillManager
from system.tool_registry import ToolRegistry, create_default_tools

logger = logging.getLogger("ahs.integration")


class SystemStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class IntegrationStats:
    tasks_processed: int = 0
    hermes_calls: int = 0
    tools_called: int = 0
    errors: int = 0
    uptime: float = 0.0
    started_at: float = field(default_factory=time.time)


class AHSIntegration:
    """Main integration layer (v2, cleaned)."""

    def __init__(self):
        self.hermes: HermesBridge | None = None
        self.tools: ToolRegistry | None = None
        self.skills: SkillManager | None = None
        self.learner: sl.SelfLearningSystem | None = None
        self.status = SystemStatus.STOPPED
        self.stats = IntegrationStats()
        self._init_components: list[str] = []
        self._event_handlers: dict[str, list[Callable]] = {}

    def initialize(self) -> dict:
        self.status = SystemStatus.STARTING
        start = time.time()
        results = {}

        # 1. Hermes Bridge
        try:
            self.hermes = HermesBridge()
            results["hermes_bridge"] = "✅"
            self._init_components.append("hermes_bridge")
        except Exception as e:
            results["hermes_bridge"] = f"❌ {e}"

        # 2. Tool Registry
        try:
            self.tools = create_default_tools()
            results["tool_registry"] = f"✅ ({len(self.tools.list())} tools)"
            self._init_components.append("tool_registry")
        except Exception as e:
            results["tool_registry"] = f"❌ {e}"

        # 3. Skill Manager
        try:
            self.skills = SkillManager()
            if self.hermes:
                self.skills.set_hermes_bridge(self.hermes)
            count = self.skills.load_all()
            results["skill_manager"] = f"✅ ({count} skills)"
            self._init_components.append("skill_manager")
        except Exception as e:
            results["skill_manager"] = f"❌ {e}"

        # 4. Self-Learning
        try:
            self.learner = sl.SelfLearningSystem()
            lr = self.learner.on_startup()
            results["self_learning"] = f"✅ ({lr['stats']['fix_rate']}%)"
            self._init_components.append("self_learning")
        except Exception as e:
            results["self_learning"] = f"❌ {e}"

        all_ok = all("✅" in v for v in results.values())
        self.status = SystemStatus.RUNNING if all_ok else SystemStatus.DEGRADED
        self.stats.uptime = time.time() - start
        self._emit("initialized", results)

        return {
            "status": self.status.value,
            "initialized": len(self._init_components),
            "results": results,
            "elapsed": round(self.stats.uptime, 2),
        }

    def process(self, task: str) -> dict:
        self.stats.tasks_processed += 1
        if not self.hermes:
            return {"response": "⚠️ Hermes not initialized"}
        try:
            result = self.hermes.send_task(task, timeout=120)
            self.stats.hermes_calls += 1
            resp = result.get("response", "")
            if not resp:
                resp = str(result)
            return {"response": str(resp)[:1000]}
        except Exception as e:
            self.stats.errors += 1
            return {"response": f"❌ {e}"}

    def get_status(self) -> dict:
        return {
            "name": "AHS-Agent-Hybrid-System",
            "version": os.environ.get("AHS_VERSION", "1.0.0"),
            "status": self.status.value,
            "uptime": round(time.time() - self.stats.started_at),
            "components": {
                "hermes_bridge": self.hermes is not None,
                "tool_registry": self.tools is not None,
                "skill_manager": self.skills is not None,
                "self_learning": self.learner is not None,
            },
            "stats": {
                "tasks": self.stats.tasks_processed,
                "hermes_calls": self.stats.hermes_calls,
                "errors": self.stats.errors,
            },
        }

    def shutdown(self):
        self.status = SystemStatus.STOPPED
        self._emit("shutdown", {})

    def on(self, event: str, handler: Callable):
        self._event_handlers.setdefault(event, []).append(handler)

    def _emit(self, event: str, data: Any):
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                pass


def bootstrap() -> AHSIntegration:
    print("🤝 AHS v1.0 Integration — Initializing...")
    ahs = AHSIntegration()
    result = ahs.initialize()
    print(f"  ✅ result")
    return ahs
