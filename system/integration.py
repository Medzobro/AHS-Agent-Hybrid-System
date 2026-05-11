#!/usr/bin/env python3
"""
AHS - Integration Layer
=========================
Integration layer that connects all AHS components together.

Provides:
  - Unified interface for all systems
  - Component initialization and startup
  - Lifecycle management
  - Single entry point
"""

import json, os, sys, time, uuid, threading, logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.orchestrator import HybridOrchestrator, TaskType
from core.agent_loop import HybridAgent
from bridge.hermes_bridge import HermesBridge
from skills.hybrid_skills import HybridSkills
from skills.synthesizer import ResponseSynthesizer
from skills.code_assistant import CodeAssistant
from system.multi_agent import MultiAgentOrchestrator, AgentWorker, AgentRole
from system.tool_registry import ToolRegistry, create_default_tools, dump_tools_registry
from system.skill_manager import SkillManager, SkillCategory
from system.config_manager import ConfigManager
from system.doctor import Doctor
import system.self_learn as sl

logger = logging.getLogger("ahs.integration")


class SystemStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class IntegrationStats:
    """Integration statistics"""
    tasks_processed: int = 0
    hermes_calls: int = 0
    tools_called: int = 0
    skills_executed: int = 0
    errors: int = 0
    uptime: float = 0.0
    started_at: float = field(default_factory=time.time)


class AHSIntegration:
    """
    Main integration layer — connects everything together.

    Components:
      - Orchestrator: Classification and planning
      - HermesBridge: Communication with Hermes
      - ToolRegistry: Tools
      - SkillManager: Skills
      - MultiAgent: Multiple agents
      - ConfigManager: Configuration
      - Doctor: Health checks
    """

    def __init__(self):
        self.config = ConfigManager()
        self.orchestrator: Optional[HermesBridge] = None
        self.agent: Optional[HermesBridge] = None
        self.hermes: Optional[HermesBridge] = None
        self.tools: Optional[ToolRegistry] = None
        self.skills: Optional[SkillManager] = None
        self.multi_agent: Optional[MultiAgentOrchestrator] = None
        self.doctor: Optional[Doctor] = None
        self.synth: Optional[ResponseSynthesizer] = None
        self.code: Optional[CodeAssistant] = None
        self.hybrid_skills: Optional[HybridSkills] = None

        self.status = SystemStatus.STOPPED
        self.stats = IntegrationStats()
        self._components_initialized: List[str] = []
        self._event_handlers: Dict[str, List[Callable]] = {}

    def initialize(self) -> Dict:
        """Initialize all system components"""
        self.status = SystemStatus.STARTING
        start = time.time()
        results = {}

        # 1. Core
        try:
            self.orchestrator = HybridOrchestrator()
            self.agent = HybridAgent()
            results["orchestrator"] = "✅"
            self._components_initialized.append("orchestrator")
        except Exception as e:
            results["orchestrator"] = f"❌ {e}"

        # 2. Bridge
        try:
            self.hermes = HermesBridge()
            results["hermes_bridge"] = "✅"
            self._components_initialized.append("hermes_bridge")
        except Exception as e:
            results["hermes_bridge"] = f"❌ {e}"

        # 3. Tools
        try:
            self.tools = create_default_tools()
            results["tool_registry"] = f"✅ ({len(self.tools.list())} tools)"
            self._components_initialized.append("tool_registry")
        except Exception as e:
            results["tool_registry"] = f"❌ {e}"

        # 4. Skills
        try:
            self.skills = SkillManager()
            if self.hermes:
                self.skills.set_hermes_bridge(self.hermes)
            count = self.skills.load_all()
            results["skill_manager"] = f"✅ ({count} skills loaded)"
            self._components_initialized.append("skill_manager")
        except Exception as e:
            results["skill_manager"] = f"❌ {e}"

        # 5. Multi-Agent
        try:
            self.multi_agent = MultiAgentOrchestrator()
            self.multi_agent.register_default_workers()
            results["multi_agent"] = f"✅ ({len(self.multi_agent.workers)} workers)"
            self._components_initialized.append("multi_agent")
        except Exception as e:
            results["multi_agent"] = f"❌ {e}"

        # 6. Doctor
        try:
            self.doctor = Doctor()
            results["doctor"] = "✅"
            self._components_initialized.append("doctor")
        except Exception as e:
            results["doctor"] = f"❌ {e}"

        # 7. Skills Modules
        try:
            self.synth = ResponseSynthesizer()
            self.code = CodeAssistant()
            self.hybrid_skills = HybridSkills()
            results["skill_modules"] = "✅"
            self._components_initialized.append("skill_modules")
        except Exception as e:
            results["skill_modules"] = f"❌ {e}"

        # 8. Config
        try:
            self.config.load_env()
            results["config"] = "✅"
            self._components_initialized.append("config")
        except Exception as e:
            results["config"] = f"❌ {e}"

        # 9. Self-Learning
        try:
            self.learner = sl.SelfLearningSystem()
            learn_result = self.learner.on_startup()
            results["self_learning"] = f"✅ ({learn_result['stats']['fix_rate']}% fix rate)"
            self._components_initialized.append("self_learning")
        except Exception as e:
            results["self_learning"] = f"❌ {e}"

        elapsed = time.time() - start
        all_ok = all("✅" in v for v in results.values())
        self.status = SystemStatus.RUNNING if all_ok else SystemStatus.DEGRADED

        self.stats.uptime = elapsed
        self._emit("initialized", results)

        return {
            "status": self.status.value,
            "initialized": len(self._components_initialized),
            "total_components": len(results),
            "results": results,
            "elapsed": round(elapsed, 2),
        }

    def process(self, task: str, mode: str = "auto", **kwargs) -> Dict:
        """Process task using best mode"""
        self.stats.tasks_processed += 1

        if mode == "auto":
            if not self.hermes:
                return {"response": "⚠️ النظام لم يتم تهيئته بعد"}
            mode = self._auto_select_mode(task)

        processors = {
            "quick": self._process_quick,
            "hybrid": self._process_hybrid,
            "code": self._process_code,
            "deep": self._process_deep,
            "flow": self._process_flow,
        }

        processor = processors.get(mode, self._process_hybrid)
        try:
            result = processor(task)
            result["mode"] = mode
            return result
        except Exception as e:
            self.stats.errors += 1
            return {"response": f"❌ {e}", "mode": mode, "error": str(e)}

    def _auto_select_mode(self, task: str) -> str:
        """Auto-select best mode"""
        task_lower = task.lower()

        if any(w in task_lower for w in ["كود", "برمج", "code", "python", "برنامج"]):
            return "code"
        if any(w in task_lower for w in ["ابحث", "بحث", "what", "why", "كيف"]):
            return "deep"
        if any(w in task_lower for w in ["مرحبا", "hi", "hello", "تمام", "من"]):
            return "quick"
        if len(task) > 200:
            return "flow"

        return "hybrid"

    def _process_quick(self, task: str) -> Dict:
        """Quick processing (OpenClaw only)"""
        return {"response": "✅ تم", "elapsed": 0.01}

    def _process_hybrid(self, task: str) -> Dict:
        """Hybrid processing (OpenClaw + Hermes)"""
        if not self.synth:
            return {"response": "⚠️ الوضع الهجين غير متاح"}
        result = self.synth.synthesize(task)
        self.stats.hermes_calls += 1
        return {"response": result["final"], "elapsed": result["elapsed"]}

    def _process_code(self, task: str) -> Dict:
        """Code processing"""
        if not self.code:
            return {"response": "⚠️ مساعد البرمجة غير متاح"}
        result = self.code.write_code(task)
        self.stats.hermes_calls += 1
        if result.get("success"):
            return {
                "response": f"✅ كود جاهز! `{result['filename']}` ({result['lines']} سطر)",
                "elapsed": result["elapsed"],
                "file": result["filepath"],
            }
        return {"response": f"❌ {result.get('error')}"}

    def _process_deep(self, task: str) -> Dict:
        """Deep processing (Hermes)"""
        if not self.hermes:
            return {"response": "⚠️ Hermes غير متاح"}
        result = self.hermes.send_task(task, thinking_mode=True)
        self.stats.hermes_calls += 1
        resp = result.get("response", {})
        content = resp.get("content", "") or ""
        return {"response": content[:600], "elapsed": result.get("elapsed", 0)}

    def _process_flow(self, task: str) -> Dict:
        """Multi-step flow processing"""
        if not self.multi_agent:
            return {"response": "⚠️ النظام متعدد الوكلاء غير متاح"}
        result = self.multi_agent.run_all()
        self.stats.hermes_calls += result.get("completed", 0)
        return {"response": f"✅ {result['completed']} مهام منجزة", "details": result}

    def health_check(self) -> Dict:
        """Full health check"""
        if not self.doctor:
            self.doctor = Doctor()
        return self.doctor.diagnose()

    def get_status(self) -> Dict:
        """Full system status"""
        config_summary = self.config.summary() if self.config else {}

        return {
            "name": "AHS-Agent-Hybrid-System",
            "version": self.config.get("ahs.version", "0.2.0"),
            "status": self.status.value,
            "uptime_seconds": round(time.time() - self.stats.started_at),
            "components": {
                "orchestrator": self.orchestrator is not None,
                "hermes_bridge": self.hermes is not None,
                "tool_registry": self.tools is not None,
                "skill_manager": self.skills is not None,
                "multi_agent": self.multi_agent is not None,
                "doctor": self.doctor is not None,
                "synthesizer": self.synth is not None,
                "code_assistant": self.code is not None,
            },
            "stats": {
                "tasks_processed": self.stats.tasks_processed,
                "hermes_calls": self.stats.hermes_calls,
                "tools_called": self.stats.tools_called,
                "skills_executed": self.stats.skills_executed,
                "errors": self.stats.errors,
            },
            "config": {
                "model": config_summary.get("model"),
                "provider": config_summary.get("provider"),
                "profile": config_summary.get("profile"),
                "valid": config_summary.get("valid"),
            },
            "tools_count": len(self.tools.list()) if self.tools else 0,
            "skills_count": len(self.skills.list()) if self.skills else 0,
            "workers_count": len(self.multi_agent.workers) if self.multi_agent else 0,
        }

    def shutdown(self):
        """Shutdown system"""
        self.status = SystemStatus.STOPPED
        self._emit("shutdown", {})
        logger.info("AHS shutdown complete")

    def on(self, event: str, handler: Callable):
        """Register system event listener"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def learn_report(self) -> Dict:
        """تقرير التعلم الذاتي"""
        if not hasattr(self, 'learner'):
            return {"status": "not_initialized"}
        return self.learner.report()

    def suggest_improvements(self) -> List:
        """اقتراح تحسينات"""
        if not hasattr(self, 'learner'):
            return []
        return self.learner.suggest_improvements()

    def auto_fix(self) -> Dict[str, bool]:
        """محاولة إصلاح كل الملفات تلقائياً"""
        if not hasattr(self, 'learner'):
            return {}
        return self.learner.auto_fix_files()

    def _emit(self, event: str, data: Any):
        """Emit event"""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception:
                pass


def bootstrap() -> AHSIntegration:
    """
    Initialize and start the entire system.
    هذه الدالة تستخدم كنقطة دخول.
    """
    print("🤝 AHS Integration - Initializing...")
    ahs = AHSIntegration()
    result = ahs.initialize()
    print(f"  ✅ {result['initialized']}/{result['total_components']} components")
    print(f"  ⏱ {result['elapsed']}s")
    return ahs


def process_task(task: str, mode: str = "auto") -> str:
    """Process task (quick function for direct use)"""
    ahs = bootstrap()
    result = ahs.process(task, mode=mode)
    return result.get("response", str(result))


if __name__ == "__main__":
    # Initialize
    ahs = bootstrap()

    print("\n🧪 Test:")
    tasks = [
        ("من أنت", "hybrid"),
        ("اكتب كود يقول مرحبا", "code"),
    ]
    for task, mode in tasks:
        print(f"\n📥 [{mode}] {task}")
        result = ahs.process(task, mode=mode)
        print(f"📤 {result.get('response', '')[:200]}")

    print("\n📊 Status:")
    status = ahs.get_status()
    for k, v in status.items():
        if not isinstance(v, dict):
            print(f"  {k}: {v}")

    print("\n✅ Integration Test Complete")
