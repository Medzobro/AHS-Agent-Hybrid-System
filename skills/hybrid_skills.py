#!/usr/bin/env python3
"""
AHS - Hybrid Skills
==================
Skills that use OpenClaw + Hermes together to execute a single task.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.hermes_bridge import HermesBridge


class HybridSkills:
    """
    Hybrid Skills — كل مهارة تستخدم OpenClaw و Hermes معاً.
    """

    def __init__(self):
        self.hermes = HermesBridge()

    def research_and_summarize(self, topic: str) -> dict:
        """مهارة: بحث + تلخيص (Hermes يبحث + OpenClaw يلخص)"""
        result = self.hermes.send_task(
            task=f"""
ابحث عن معلومات محدثة حول: {topic}
استخدم الأدوات المتاحة: web_fetch, search_files, delegate_task
اجمع المعلومات من 3 مصادر على الأقل.
قدم ملخصاً منظمًا.

المطلوب:
1. مصدرين أو أكثر
2. النقاط الرئيسية
3. خلاصة
""",
            skills="research,llm-wiki,systematic-debugging",
            thinking_mode=True,
            timeout=180
        )

        return result

    def code_review(self, code: str) -> dict:
        """مهارة: مراجعة كود (Hermes يحلل + OpenClaw يقرر)"""
        result = self.hermes.send_task(
            task=f"""
راجع هذا الكود بدقة:

```python
{code[:2000]}
```

حلل:
1. مشاكل محتملة
2. تحسينات أداء
3. أفضل الممارسات

كن دقيقاً ومحدداً.
""",
            skills="systematic-debugging,dogfood",
            thinking_mode=True,
            timeout=120
        )

        return result

    def plan_project(self, description: str) -> dict:
        """مهارة: تخطيط مشروع (Hermes يفكر + OpenClaw ينفذ)"""
        result = self.hermes.send_task(
            task=f"""
خطط لمشروع: {description}

قدم:
1. **تحليل المتطلبات** — ماذا نحتاج بالضبط
2. **الهيكلة** — بنية المشروع
3. **الخطوات** — مهام محددة مرتبة
4. **المخاطر** — مشاكل محتملة
5. **الجدول الزمني** — تقدير المدة

كن عملياً ومحدداً.
""",
            skills="writing-plans,systematic-debugging",
            thinking_mode=True,
            timeout=120
        )

        return result

    def learn_new_skill(self, skill_name: str) -> dict:
        """مهارة: تعلم شيء جديد (Hermes يدرس + OpenClaw يطبق)"""
        result = self.hermes.send_task(
            task=f"""
تعلم واشرح: {skill_name}

غط:
1. ما هو؟ تعريف بسيط
2. أهم المفاهيم
3. تطبيق عملي (كود أو مثال)
4. موارد للتعلم (روابط)
5. كيف نستخدمه في مشروعنا AHS

اجعل الشرح عملياً ومناسباً لمطوري الأنظمة.
""",
            skills="research,arxiv,systematic-debugging",
            thinking_mode=True,
            timeout=180
        )

        return result


# اختبار
if __name__ == "__main__":
    skills = HybridSkills()

    print("🧪 اختبار المهارات الهجينة")
    result = skills.research_and_summarize("AI Agent أفضل الممارسات 2026")
    if result.get("success"):
        resp = result.get("response", {})
        print(f"✅ {resp.get('content', '')[:300]}")
    else:
        print(f"❌ {result.get('error')}")
