"""
AHS - Response Synthesizer
=============================
يجمع بين OpenClaw (سريع) و Hermes (عميق) في رد واحد متكامل.
"""

import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bridge.hermes_bridge import HermesBridge
from typing import Dict

class ResponseSynthesizer:
    """
    يدمج ردود OpenClaw و Hermes في رد واحد ذكي.
    - OpenClaw: يفهم السياق والمهمة بسرعة
    - Hermes: يفكر عميقاً ويحلل
    - Synthesis: يجمع الأفضل من الاثنين
    """

    def __init__(self):
        self.hermes = HermesBridge()

    def synthesize(self, task: str) -> Dict:
        """يجمع OpenClaw + Hermes في رد واحد"""
        start = time.time()

        # 1. OpenClaw يحلل المهمة سريعاً (فوري - بدون API)
        openclaw_analysis = self._openclaw_quick(task)

        # 2. Hermes يفكر عميقاً (مع DeepSeek R1)
        hermes_result = self.hermes.send_task(
            task=f"أجب على هذا السؤال بإجابة مباشرة ومفيدة:\n{task}",
            skills="dogfood",
            thinking_mode=True,
            timeout=90
        )

        # 3. أستخرج رد Hermes
        hermes_response = ""
        if hermes_result.get("success"):
            resp = hermes_result.get("response", {})
            hermes_response = resp.get("content", "")
            if not hermes_response and resp.get("content_raw"):
                hermes_response = resp["content_raw"]
            hermes_thinking = resp.get("reasoning", "")
        else:
            hermes_response = f"⚠️ {hermes_result.get('error', 'فشل')}"

        elapsed = time.time() - start

        # 4. أصنع الرد النهائي
        final = self._build_response(task, openclaw_analysis, hermes_response, elapsed)

        return {
            "task": task,
            "openclaw": openclaw_analysis,
            "hermes": hermes_response[:300],
            "final": final,
            "elapsed": round(elapsed, 1),
        }

    def _openclaw_quick(self, task: str) -> str:
        """OpenClaw يحلل المهمة سريعاً"""
        task_l = task.lower()

        if any(w in task_l for w in ["مرحبا", "hello", "اهلا"]):
            return "تحية"
        if any(w in task_l for w in ["من", "what", "who", "وش"]):
            return "سؤال معرفي"
        if any(w in task_l for w in ["ابحث", "بحث", "learn", "study"]):
            return "طلب بحث/تعلم"
        if any(w in task_l for w in ["اكتب", "برمج", "كود", "code"]):
            return "طلب برمجة/كود"
        if any(w in task_l for w in ["خطط", "plan", "project"]):
            return "طلب تخطيط مشروع"
        return "مهمة عامة"

    def _build_response(self, task: str, analysis: str, hermes: str, elapsed: float) -> str:
        """بناء الرد النهائي المدمج"""
        # بداية مختصرة
        if not hermes:
            return "🤝 **AHS جاهز** — أرسل مهمتك"

        hermes_clean = hermes[:600]
        if len(hermes) > 600:
            hermes_clean += "..."

        return f"""🤝 **AHS Hybrid Agent**

{hermes_clean}

⚡ {elapsed:.1f}s | {analysis}"""


if __name__ == "__main__":
    s = ResponseSynthesizer()
    r = s.synthesize("وش معنى AI Agent؟")
    print(r["final"])
