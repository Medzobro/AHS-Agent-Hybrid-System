#!/usr/bin/env python3
"""
AHS - Agent Hybrid System
=========================
النواة المركزية — تنسيق العمل بين OpenClaw و Hermes

المبدأ: كل مهمة تُحلَّل ثم تُوجَّه للطرف الأنسب.
- OpenClaw: تنفيذ سريع، أوامر، تحكم
- Hermes: تفكير عميق، بحث، مهارات متعددة
"""

import json
import os
import sys
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TaskType(Enum):
    """أنواع المهام — من يصلح لها"""
    QUICK = "quick"           # رد سريع → OpenClaw
    DEEP = "deep"             # تفكير عميق → Hermes
    HYBRID = "hybrid"         # الاثنان معاً
    SKILL = "skill"           # مهارة محددة → Hermes
    CODE = "code"             # برمجة → OpenClaw + Hermes
    COMMAND = "command"       # أمر مباشر → OpenClaw


class HybridOrchestrator:
    """
    العقل المدبر للنظام الهجين.
    يقرر من ينفذ المهمة ويتابع النتائج.
    """

    def __init__(self):
        self.memory_file = os.path.join(
            os.path.dirname(__file__), "../bridge/shared_memory.json"
        )
        self.history: List[Dict] = []
        self.memory: Dict = self._load_memory()

    def _load_memory(self) -> Dict:
        """تحميل الذاكرة المشتركة"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "learnings": [], "skills": []}

    def _save_memory(self):
        """حفظ الذاكرة المشتركة"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def classify_task(self, task: str) -> Tuple[TaskType, str]:
        """
        تحليل المهمة وتحديد نوعها والجهة المناسبة.
        """
        task_lower = task.lower()

        # كشف النمط
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

        # المهام المعقدة → Hermes
        if len(task) > 200:
            return TaskType.HYBRID, "long_task"

        return TaskType.HYBRID, "default"

    def plan_execution(self, task: str, task_type: TaskType) -> Dict:
        """
        تخطيط تنفيذ المهمة — من يفعل ماذا.
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
        """تسجيل درس جديد في الذاكرة المشتركة"""
        self.memory["learnings"].append({
            "key": key,
            "value": value,
            "source": source,
            "timestamp": time.time()
        })
        # نحتفظ بآخر 100 درس
        self.memory["learnings"] = self.memory["learnings"][-100:]
        self._save_memory()

    def get_relevant_learnings(self, task: str, limit: int = 5) -> List[Dict]:
        """استرجاع الدروس المتعلقة بالمهمة"""
        learnings = self.memory.get("learnings", [])
        task_lower = task.lower()
        relevant = []
        for l in learnings:
            key = l.get("key", "").lower()
            if any(word in key for word in task_lower.split()):
                relevant.append(l)
        return relevant[:limit]

    def run(self, task: str, user_id: str = "user") -> Dict:
        """
        تشغيل المهمة خلال النظام الهجين.
        هذه الدالة تستدعى من OpenClaw عند ورود أمر.
        """
        # تسجيل المهمة
        self.history.append({
            "user_id": user_id,
            "task": task,
            "timestamp": time.time(),
        })

        # تصنيف وتخطيط
        task_type, reason = self.classify_task(task)
        plan = self.plan_execution(task, task_type)

        # استرجاع الدروس السابقة
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


# اختبار سريع
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
        print(f"📥 المهمة: {task}")
        result = orch.run(task)
        print(f"📊 التصنيف: {result['classification']['type']}")
        print(f"📋 الخطة:")
        for step in result["plan"]["steps"]:
            print(f"   {step['action']} ← {step['by']}")
