#!/usr/bin/env python3
"""
AHS - Agent Loop
=================
الحلقة الرئيسية للنظام الهجين.
تستقبل الأوامر → تصنف → تخطط → تنفذ → ترد.
"""

import json
import os
import sys
import time
import traceback
from typing import Dict, List, Optional, Any

# إضافة المسارات
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import HybridOrchestrator, TaskType
from bridge.hermes_bridge import HermesBridge


class HybridAgent:
    """
    الـ Agent الهجين الرئيسي.
    يجمع OpenClaw + Hermes في حلقة واحدة.
    """

    def __init__(self):
        self.orchestrator = HybridOrchestrator()
        self.hermes = HermesBridge()
        self.history: List[Dict] = []
        self.version = "0.1.0"
        self.name = "AHS (Agent Hybrid System)"

    def process(self, task: str, user_id: str = "user") -> Dict:
        """
        معالجة مهمة خلال النظام الهجين.

        1. تحليل المهمة
        2. التخطيط
        3. تنفيذ الخطط (OpenClaw و/أو Hermes)
        4. تجميع النتيجة
        5. حفظ في الذاكرة
        6. الرد
        """
        start_time = time.time()

        # الخطوة 1-2: تحليل وتخطيط
        classification = self.orchestrator.classify_task(task)
        plan = self.orchestrator.plan_execution(task, classification[0])

        # الخطوة 3: التنفيذ
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

            # إذا كان الـ step الأخير من OpenClaw والسابق Hermes
            if assignee == "openclaw" and action in ["respond", "summarize", "synthesize"]:
                final_response = step_result or self._openclaw_respond(task, execution_log)

        # إذا ما حصلنا رد نهائي
        if not final_response:
            final_response = self._openclaw_respond(task, execution_log)

        # الخطوة 5: حفظ في الذاكرة
        self.orchestrator.record_learning(
            key=f"task_{len(self.history)}",
            value={
                "task": task,
                "type": classification[0].value,
                "response_summary": final_response[:100],
            }
        )

        # إحصائيات
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

        # حفظ التاريخ
        self.history.append(result)

        return result

    def _execute_step(self, action: str, assignee: str, task: str, log: List) -> Optional[str]:
        """تنفيذ خطوة واحدة من الخطة"""
        try:
            if assignee == "hermes":
                return self._hermes_execute(action, task, log)
            elif assignee == "openclaw":
                return None  # OpenClaw يتولى الرد مباشرة
        except Exception as e:
            return f"⚠️ خطأ في التنفيذ: {str(e)}"
        return None

    def _hermes_execute(self, action: str, task: str, log: List) -> str:
        """تنفيذ خطوة عبر Hermes مع وضع التفكير"""
        # مهم: نستخدم صيغة بسيطة لا تحفز Hermes على استخدام أدوات غير متاحة
        hermes_task = (
            f"فكر في هذا السؤال وأجب فقط:\n"
            f"السؤال: {task}\n\n"
            f"قدم إجابة مباشرة ومفيدة."
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
                return f"[تفكير Hermes]\n{reasoning[:300]}\n\n[الرد]\n{content[:500]}"
            return content[:500]
        else:
            return f"⚠️ Hermes: {result.get('error', 'فشل غير معروف')}"

    def _openclaw_respond(self, task: str, log: List) -> str:
        """OpenClaw يرد مباشرة (أنا)"""
        # هذه الدالة تستدعى من OpenClaw نفسه
        # الرد يكتب هنا كملاذ أخير
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
        """رد مباشر من OpenClaw لمهام بسيطة"""
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

        return f"تم استلام المهمة. سأحللها مع Hermes وأعود لك بالنتيجة."

    def status(self) -> Dict:
        """حالة النظام"""
        return {
            "name": self.name,
            "version": self.version,
            "tasks_processed": len(self.history),
            "hermes_connected": True,
            "model": "DeepSeek R1 (reasoner)",
            "last_task": self.history[-1] if self.history else None,
        }


# اختبار
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
