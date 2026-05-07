#!/usr/bin/env python3
"""
AHS - Orchestrator V2
======================
التدفق متعدد الخطوات — OpenClaw و Hermes يتعاونون خطوة بخطوة.

بدلاً من "اسأل Hermes وخلاص"، هذا الأوركيستريتور يدير
تدفقاً كاملاً:
  OpenClaw → يفهم → يخطط → Hermes → يفكر → OpenClaw → ينفذ → يرد
"""

import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bridge.hermes_bridge import HermesBridge
from typing import Dict, List, Optional


class HybridFlow:
    """
    تدفق هجين متكامل بين OpenClaw و Hermes.
    كل خطوة يحددها النظام حسب نوع المهمة.
    """

    def __init__(self):
        self.hermes = HermesBridge()
        self.steps_log: List[Dict] = []

    def run(self, task: str) -> Dict:
        """تشغيل التدفق الهجين الكامل"""
        self.steps_log = []
        start = time.time()

        task_lower = task.lower()

        # === تحديد نوع التدفق ===
        if any(w in task_lower for w in ["كود", "برمج", "code", "python", "برنامج"]):
            flow_type = "code"
        elif any(w in task_lower for w in ["ابحث", "بحث", "what", "شرح", "معنى"]):
            flow_type = "research"
        else:
            flow_type = "general"

        # === OpenClaw: الخطوة 1 — فهم المهمة ===
        self._log("openclaw", "understand", f"تحليل: {flow_type}")

        # === OpenClaw: الخطوة 2 — تخطيط ===
        plan = self._plan(flow_type, task)
        self._log("openclaw", "plan", f"الخطة: {len(plan)} خطوات")

        # === التنفيذ ===
        for i, step in enumerate(plan):
            actor = step["actor"]
            action = step["action"]

            if actor == "hermes":
                result = self._hermes_step(action, task)
            else:
                result = self._openclaw_step(action, task, step)

            self._log(actor, action, result[:100] if result else "تم")
            self.steps_log[-1]["full"] = result

        # === OpenClaw: الخطوة الأخيرة — الرد ===
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
        """تخطيط الخطوات حسب نوع المهمة"""
        if flow_type == "code":
            return [
                {"actor": "hermes", "action": "write_code", "prompt": f"اكتب كود Python: {task}"},
            ]
        elif flow_type == "research":
            return [
                {"actor": "hermes", "action": "deep_think", "prompt": f"حلل واشرح: {task}"},
            ]
        else:
            return [
                {"actor": "hermes", "action": "answer", "prompt": f"أجب: {task}"},
            ]

    def _hermes_step(self, action: str, task: str) -> str:
        """تشغيل خطوة عبر Hermes"""
        prompt = f"فكر وأجب بدقة:\n{task}"
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
        """OpenClaw ينفذ خطوة"""
        if action == "understand":
            return "تم فهم المهمة"
        elif action == "plan":
            return f"تم تخطيط {step.get('plan_type', 'عام')}"
        elif action == "save":
            return "تم الحفظ"
        return "تم"

    def _build_final_response(self) -> str:
        """بناء الرد النهائي من كل الخطوات"""
        hermes_outputs = [
            s.get("full", "")
            for s in self.steps_log
            if s.get("actor") == "hermes" and s.get("full")
        ]

        if not hermes_outputs:
            return "🤝 **AHS** — تم تنفيذ المهمة"

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
        """عرض سجل الخطوات"""
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
