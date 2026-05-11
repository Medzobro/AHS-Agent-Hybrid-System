#!/usr/bin/env python3
"""
AHS - Code Assistant (Hybrid)
================================
OpenClaw + Hermes يكتبون كود مع بعض.

التدفق:
  1. OpenClaw: يفهم الطلب ويحضّر السياق
  2. Hermes: يكتب الكود بتفكير عميق
  3. OpenClaw: يحفظ الكود في ملف
  4. OpenClaw: يقدم ملخص
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bridge.hermes_bridge import HermesBridge

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class CodeAssistant:
    """
    مساعد برمجة هجين.
    - أكتب كود (OpenClaw يحفظ، Hermes يكتب)
    - راجع كود (Hermes يراجع، OpenClaw يلخص)
    - طور كود (Hermes يقترح، OpenClaw ينفذ)
    """

    def __init__(self):
        self.hermes = HermesBridge()

    def write_code(self, request: str, filename: str | None = None,
                   language: str = "python") -> dict:
        """
        اكتب كود: Hermes يكتب الكود ← OpenClaw يحفظه.
        """
        start = time.time()

        # 1. OpenClaw يحدد اسم الملف
        if not filename:
            base = request.lower().replace(" ", "_")[:20]
            filename = f"{base}.{language.replace('python', 'py')}"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # 2. Hermes يكتب الكود
        hermes_task = f"""
اكتب كود {language} كامل ومفصل للمهمة التالية:

{request}

المطلوب:
- كود كامل جاهز للتشغيل
- تعليقات بالعربي (شرح كل جزء)
- معالجة الأخطاء
- مثال استخدام

اكتب الكود فقط بين <code> و </code>
"""
        hermes_result = self.hermes.send_task(
            task=hermes_task,
            skills="dogfood",
            thinking_mode=True,
            timeout=120
        )

        # 3. OpenClaw يستخرج الكود ويحفظه
        code = ""
        if hermes_result.get("success"):
            resp = hermes_result.get("response", {})
            raw = resp.get("content", "") or resp.get("content_raw", "")

            # استخراج الكود من بين <code> tags
            if "<code>" in raw and "</code>" in raw:
                code = raw.split("<code>")[1].split("</code>")[0].strip()
            else:
                # جرب استخراج ```language
                markers = [f"```{language}", "```python", "```"] if language == "python" else ["```"]
                for m in markers:
                    if m in raw:
                        parts = raw.split(m)
                        if len(parts) >= 2:
                            code = parts[1].strip()
                            if code.endswith("```"):
                                code = code[:-3].strip()
                            break

            if not code:
                code = raw  # استخدام النص كاملاً
        else:
            return {"success": False, "error": hermes_result.get("error")}

        # 4. OpenClaw يحفظ الملف
        try:
            with open(filepath, "w") as f:
                f.write(code)
            saved = True
        except Exception as e:
            saved = False
            filepath = str(e)

        elapsed = time.time() - start

        return {
            "success": True,
            "language": language,
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "lines": len(code.split("\n")),
            "chars": len(code),
            "saved": saved,
            "code": code[:200],
            "hermes_raw": raw[:300],
            "elapsed": round(elapsed, 1),
        }

    def review_code(self, code: str) -> dict:
        """
        راجع كود: Hermes يحلل ← OpenClaw يلخص.
        """
        start = time.time()

        # 1. OpenClaw يقرأ الكود ويحضره
        code_preview = code[:2000]

        # 2. Hermes يراجع
        hermes_result = self.hermes.send_task(
            task=f"""
راجع هذا الكود بدقة:

```python
{code_preview}
```

حلل:
1. مشاكل أمنية (Security Issues)
2. أخطاء منطقية (Logic Errors)
3. تحسينات أداء (Performance Improvements)
4. أفضل الممارسات (Best Practices)

لكل نقطة: اشرح المشكلة + اقترح حل.
""",
            skills="dogfood",
            thinking_mode=True,
            timeout=90
        )

        elapsed = time.time() - start
        review = ""
        if hermes_result.get("success"):
            resp = hermes_result.get("response", {})
            review = resp.get("content", "") or resp.get("content_raw", "")

        return {
            "success": bool(review),
            "review": review[:500],
            "elapsed": round(elapsed, 1),
        }

    def improve_code(self, code: str, instructions: str) -> dict:
        """
        طور كود: Hermes يقترح تحسينات ← OpenClaw ينفذها.
        """
        start = time.time()

        code_preview = code[:2000]

        # Hermes يقترح التحسينات
        hermes_result = self.hermes.send_task(
            task=f"""
الكود الحالي:
```python
{code_preview}
```

مطلوب تحسين: {instructions}

اكتب الكود المحسّن كاملاً بين <code> و </code>
""",
            skills="dogfood",
            thinking_mode=True,
            timeout=120
        )

        improved_code = ""
        if hermes_result.get("success"):
            resp = hermes_result.get("response", {})
            raw = resp.get("content", "") or resp.get("content_raw", "")
            if "<code>" in raw and "</code>" in raw:
                improved_code = raw.split("<code>")[1].split("</code>")[0].strip()
            else:
                improved_code = raw

        elapsed = time.time() - start

        return {
            "success": bool(improved_code),
            "code": improved_code[:200],
            "elapsed": round(elapsed, 1),
        }

    def list_generated(self) -> list:
        """عرض الملفات المولّدة"""
        files = []
        if os.path.exists(OUTPUT_DIR):
            for f in os.listdir(OUTPUT_DIR):
                fp = os.path.join(OUTPUT_DIR, f)
                files.append({
                    "name": f,
                    "size": os.path.getsize(fp),
                    "lines": len(open(fp).read().splitlines()),
                })
        return files


if __name__ == "__main__":
    c = CodeAssistant()
    print("🧪 Code Assistant Hybrid")
    r = c.write_code("دالة تقرأ ملف JSON وترجع البيانات", language="python")
    print(f"✅ {r['filename']} ({r['lines']} سطر, {r['elapsed']}s)" if r['success'] else f"❌ {r}")
