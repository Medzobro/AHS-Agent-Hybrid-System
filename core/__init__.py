"""
AHS - Core Package
==================
النواة الأساسية للنظام — التصنيف، التخطيط، وحلقات الوكيل.

المكونات:
  - orchestrator: تصنيف المهام وتخطيط التنفيذ
  - orchestrator_v2: تدفق متعدد الخطوات للتخطيط العميق
  - agent_loop: حلقة الوكيل الكاملة (استقبال ← تنفيذ ← رد)

يدعم:
  - 4 أنواع مهام: QUICK, DEEP, CODE, COMMAND
  - تخطيط تنفيذ لكل نوع
  - ذاكرة تعلم قصيرة المدى
  - Hybrid Mode: OpenClaw + Hermes معاً

الاستخدام:
  from core.orchestrator import HybridOrchestrator
  o = HybridOrchestrator()
  task_type, plan = o.classify_task("اكتب كود Python")
"""

from .orchestrator import HybridOrchestrator, TaskType
from .orchestrator_v2 import HybridOrchestratorV2
from .agent_loop import HybridAgent

__all__ = [
    "HybridOrchestrator",
    "HybridOrchestratorV2",
    "HybridAgent",
    "TaskType",
]
