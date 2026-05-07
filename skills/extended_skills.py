#!/usr/bin/env python3
"""
AHS - Extended Skills
======================
مهارات هجينة إضافية — توسع قدرات AHS.

المهارات:
  - Code Generator: يولد كوداً من الوصف
  - Text Analyzer: يحلل النصوص
  - Task Planner: يخطط المهام
  - Data Reporter: يولد تقارير
  - System Optimizer: يحسن الأداء
  - File Organizer: ينظم الملفات
  - Web Scraper: يجمع بيانات
  - Translation Helper: يساعد في الترجمة
  - Command Builder: يبني أوامر
  - Knowledge Extractor: يستخرج المعرفة
"""

import json, os, sys, time, re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class SkillBase:
    """فئة أساسية للمهارات"""
    def __init__(self, name: str, description: str, category: str = "general"):
        self.name = name
        self.description = description
        self.category = category
        self.call_count = 0

    def execute(self, **kwargs) -> Dict:
        raise NotImplementedError

    def info(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "calls": self.call_count,
        }


# =========================
#  1. Code Generator
# =========================

class CodeGenerator(SkillBase):
    """يولد كوداً من وصف طبيعي"""
    TEMPLATES = {
        "python": {
            "script": """#!/usr/bin/env python3
\"\"\"
{description}
\"\"\"

def main():
{code}

if __name__ == "__main__":
    main()
""",
            "function": """def {name}({params}):
    \"\"\"{description}\"\"\"
{code}
""",
            "class": """class {name}:
    \"\"\"{description}\"\"\"

    def __init__(self{params}):
{code}
""",
        },
        "bash": {
            "script": """#!/bin/bash
# {description}
{code}
""",
        },
        "html": {
            "page": """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{styles}
    </style>
</head>
<body>
{body}
    <script>
{scripts}
    </script>
</body>
</html>
""",
        },
    }

    def __init__(self):
        super().__init__("code_generator", "توليد كود من الوصف", "code")

    def execute(self, description: str = "", language: str = "python",
                template: str = "script", **kwargs) -> Dict:
        code_lines = self._generate_skeleton(description, language)
        code = "\n".join(code_lines)

        if language in self.TEMPLATES and template in self.TEMPLATES[language]:
            code = self.TEMPLATES[language][template].format(
                description=description,
                code=code,
                name=kwargs.get("name", "main"),
                params=kwargs.get("params", ""),
                title=kwargs.get("title", "Page"),
                lang=kwargs.get("lang", "ar"),
                styles=kwargs.get("styles", "/* styles */"),
                body=kwargs.get("body", "<h1>Hello</h1>"),
                scripts=kwargs.get("scripts", "// scripts"),
            )

        self.call_count += 1
        return {
            "code": code,
            "lines": len(code.splitlines()),
            "language": language,
            "template": template,
        }

    def _generate_skeleton(self, description: str, language: str) -> List[str]:
        """توليد هيكل الكود الأساسي من الوصف"""
        desc_lower = description.lower()
        lines = ["    # TODO: Implement this function"]

        if "للجمع" in desc_lower or "sum" in desc_lower or "جمع" in desc_lower:
            if language == "python":
                lines = [
                    "    a = float(input('Enter first number: '))",
                    "    b = float(input('Enter second number: '))",
                    "    result = a + b",
                    f"    print(f'Sum: {{result}}')",
                ]

        elif "مصفوف" in desc_lower or "array" in desc_lower or "list" in desc_lower:
            if language == "python":
                lines = [
                    "    data = []",
                    "    for i in range(10):",
                    "        data.append(i * 2)",
                    "    print(f'Data: {data}')",
                    "    return data",
                ]

        elif "ملف" in desc_lower or "file" in desc_lower:
            if language == "python":
                lines = [
                    "    filename = input('Enter filename: ')",
                    "    try:",
                    "        with open(filename, 'r') as f:",
                    "            content = f.read()",
                    "        print(f'File content ({len(content)} bytes)')",
                    "        return content",
                    "    except FileNotFoundError:",
                    "        print(f'File {filename} not found')",
                    "        return None",
                ]

        elif "api" in desc_lower or "request" in desc_lower or "url" in desc_lower:
            if language == "python":
                lines = [
                    "    import requests",
                    "    url = 'https://api.example.com/data'",
                    "    try:",
                    "        response = requests.get(url, timeout=10)",
                    "        response.raise_for_status()",
                    "        data = response.json()",
                    "        print(f'Got {len(data)} items')",
                    "        return data",
                    "    except Exception as e:",
                    "        print(f'Error: {e}')",
                    "        return None",
                ]

        elif "base de données" in desc_lower or "database" in desc_lower or "قاعدة" in desc_lower:
            if language == "python":
                lines = [
                    "    import sqlite3",
                    "    conn = sqlite3.connect('database.db')",
                    "    cursor = conn.cursor()",
                    "    cursor.execute('''CREATE TABLE IF NOT EXISTS items",
                    "        (id INTEGER PRIMARY KEY, name TEXT, value REAL)''')",
                    "    conn.commit()",
                    "    print('Database ready')",
                    "    return conn",
                ]

        return lines


# =========================
#  2. Text Analyzer
# =========================

class TextAnalyzer(SkillBase):
    """تحليل النصوص واستخراج المعلومات"""
    def __init__(self):
        super().__init__("text_analyzer", "تحليل النصوص واستخراج المعلومات", "text")

    def execute(self, text: str = "", analysis_type: str = "basic", **kwargs) -> Dict:
        result = {"text": text[:100], "type": analysis_type}

        if analysis_type == "basic":
            words = text.split()
            sentences = re.split(r'[.!?]+', text)
            result.update({
                "char_count": len(text),
                "char_no_space": len(text.replace(" ", "")),
                "word_count": len(words),
                "sentence_count": len([s for s in sentences if s.strip()]),
                "avg_word_length": round(sum(len(w) for w in words) / max(len(words), 1), 2),
            })

        elif analysis_type == "sentiment":
            positive = ["جيد", "رائع", "ممتاز", "جميل", "حب", "سعيد", "أحسنت",
                        "good", "great", "excellent", "amazing", "love", "happy"]
            negative = ["سيء", "رديء", "فاشل", "قبيح", "كره", "حزين", "غبي",
                        "bad", "terrible", "awful", "hate", "sad", "stupid"]

            words_lower = text.lower().split()
            pos_count = sum(1 for w in words_lower if w.strip(".,!?") in positive)
            neg_count = sum(1 for w in words_lower if w.strip(".,!?") in negative)
            total = pos_count + neg_count

            result.update({
                "positive_words": pos_count,
                "negative_words": neg_count,
                "sentiment_score": (pos_count - neg_count) / max(total, 1),
                "sentiment": "positive" if pos_count > neg_count else
                            "negative" if neg_count > pos_count else "neutral",
            })

        elif analysis_type == "keywords":
            words = re.findall(r'\w+', text.lower())
            word_freq = {}
            for w in words:
                if len(w) > 2:
                    word_freq[w] = word_freq.get(w, 0) + 1
            result["keywords"] = sorted(word_freq.items(), key=lambda x: -x[1])[:15]
            result["unique_words"] = len(word_freq)

        elif analysis_type == "readability":
            words = text.split()
            sentences = re.split(r'[.!?]+', text)
            valid_sentences = [s for s in sentences if s.strip()]
            total_syllables = sum(len(re.findall(r'[aeiouyAEIOUY]', w)) for w in words if re.search(r'[aeiouy]', w))

            result.update({
                "total_words": len(words),
                "total_sentences": len(valid_sentences),
                "total_syllables": total_syllables,
                "avg_sentence_length": round(len(words) / max(len(valid_sentences), 1), 1),
                "estimated_reading_time_sec": round(len(words) / 200 * 60, 0),
            })

        elif analysis_type == "structure":
            lines = text.splitlines()
            result.update({
                "total_lines": len(lines),
                "empty_lines": sum(1 for l in lines if not l.strip()),
                "code_blocks": len(re.findall(r'```', text)) // 2,
                "links": len(re.findall(r'https?://[^\s]+', text)),
                "has_arabic": bool(re.search(r'[\u0600-\u06FF]', text)),
                "has_english": bool(re.search(r'[a-zA-Z]', text)),
            })

        self.call_count += 1
        return result


# =========================
#  3. Task Planner
# =========================

class TaskPlanner(SkillBase):
    """تخطيط المهام وتقسيمها إلى خطوات"""
    def __init__(self):
        super().__init__("task_planner", "تخطيط المهام وتقسيمها", "planning")

    def execute(self, task: str = "", complexity: str = "medium", **kwargs) -> Dict:
        steps = self._generate_plan(task, complexity)

        plan = {
            "task": task,
            "complexity": complexity,
            "steps": steps,
            "total_steps": len(steps),
            "estimated_time": self._estimate_time(steps),
        }

        self.call_count += 1
        return plan

    def _generate_plan(self, task: str, complexity: str) -> List[Dict]:
        desc = task.lower()
        steps = []

        if "كود" in desc or "برمج" in desc or "code" in desc or "برنامج" in desc:
            steps = [
                {"step": 1, "action": "تحليل المتطلبات", "duration": "5m"},
                {"step": 2, "action": "تصميم الهيكل", "duration": "10m"},
                {"step": 3, "action": "كتابة الكود", "duration": "30m"},
                {"step": 4, "action": "اختبار", "duration": "15m"},
                {"step": 5, "action": "تحسين وتحقيق", "duration": "10m"},
            ]
            if complexity == "high":
                steps.extend([
                    {"step": 6, "action": "مراجعة الأمان", "duration": "10m"},
                    {"step": 7, "action": "توثيق", "duration": "15m"},
                ])

        elif "بحث" in desc or "بحث" in desc or "research" in desc or "study" in desc:
            steps = [
                {"step": 1, "action": "تحديد المصطلحات المفتاحية", "duration": "5m"},
                {"step": 2, "action": "جمع المصادر", "duration": "20m"},
                {"step": 3, "action": "تحليل المعلومات", "duration": "15m"},
                {"step": 4, "action": "تلخيص النتائج", "duration": "10m"},
            ]

        elif "فيديو" in desc or "video" in desc or "يوتيوب" in desc or "youtube" in desc:
            steps = [
                {"step": 1, "action": "كتابة النص (Script)", "duration": "30m"},
                {"step": 2, "action": "تسجيل الصوت", "duration": "15m"},
                {"step": 3, "action": "جمع المواد البصرية", "duration": "20m"},
                {"step": 4, "action": "مونتاج", "duration": "45m"},
                {"step": 5, "action": "مراجعة ونشر", "duration": "10m"},
            ]

        else:
            steps = [
                {"step": 1, "action": "فهم المهمة", "duration": "5m"},
                {"step": 2, "action": "تقسيم المهمة", "duration": "5m"},
                {"step": 3, "action": "تنفيذ", "duration": "30m"},
                {"step": 4, "action": "مراجعة", "duration": "10m"},
            ]
            if complexity == "high":
                steps.append({"step": 5, "action": "تحسين", "duration": "15m"})

        return steps

    def _estimate_time(self, steps: List[Dict]) -> str:
        total = 0
        for s in steps:
            d = s.get("duration", "0m")
            if "h" in d:
                total += int(d.replace("h", "")) * 60
            else:
                total += int(d.replace("m", ""))
        if total >= 60:
            return f"{total//60}h {total%60}m"
        return f"{total}m"


# =========================
#  4. Data Reporter
# =========================

class DataReporter(SkillBase):
    """توليد تقارير من البيانات"""
    def __init__(self):
        super().__init__("data_reporter", "توليد التقارير", "data")

    def execute(self, data: Any = None, title: str = "Report",
                format: str = "text", **kwargs) -> Dict:
        lines = []
        lines.append(f"# {title}")
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")

        if isinstance(data, dict):
            lines.append("## Data Summary")
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    lines.append(f"- **{k}**: {len(v)} items")
                else:
                    lines.append(f"- **{k}**: {v}")

        elif isinstance(data, list):
            lines.append(f"## Items ({len(data)})")
            for i, item in enumerate(data[:20], 1):
                lines.append(f"  {i}. {item}")
            if len(data) > 20:
                lines.append(f"  ... and {len(data) - 20} more")

        elif isinstance(data, str):
            lines.append(data)

        report = "\n".join(lines)

        self.call_count += 1
        return {
            "report": report,
            "title": title,
            "format": format,
            "lines": len(lines),
        }


# =========================
#  5. Command Builder
# =========================

class CommandBuilder(SkillBase):
    """بناء أوامر shell معقدة"""
    def __init__(self):
        super().__init__("command_builder", "بناء أوامر shell", "tools")

    def execute(self, description: str = "", os_type: str = "linux", **kwargs) -> Dict:
        desc = description.lower()
        commands = []
        explanation = []

        if "ملف" in desc or "file" in desc:
            if "بحث" in desc or "find" in desc or "search" in desc:
                commands.append("find . -type f -name '*.py' | head -20")
                explanation.append("البحث عن ملفات Python")
            elif "حذف" in desc or "delete" in desc or "remove" in desc:
                commands.append("rm -rf ./temp/*")
                explanation.append("حذف الملفات المؤقتة (⚠️ انتبه!)")
            elif "نسخ" in desc or "copy" in desc:
                commands.append("cp -r source/ destination/")
                explanation.append("نسخ المجلد")
            elif "ضغط" in desc or "zip" in desc or "compress" in desc:
                commands.append("tar -czvf archive.tar.gz ./folder/")
                explanation.append("ضغط المجلد")

        elif "docker" in desc:
            commands.append("docker ps")
            commands.append("docker images")
            commands.append("docker system df")
            explanation.extend(["عرض الحاويات", "عرض الصور", "حجم الاستخدام"])

        elif "git" in desc:
            commands.append("git status")
            commands.append("git log --oneline -10")
            commands.append("git branch -a")
            explanation.extend(["حالة الـ repo", "آخر 10 commits", "جميع الفروع"])

        elif "شبكة" in desc or "network" in desc:
            commands.append("ss -tuln")
            commands.append("ip addr show")
            explanation.extend(["المنافذ المفتوحة", "عناوين الشبكة"])

        elif "نظام" in desc or "system" in desc:
            commands.append("top -bn1 | head -20")
            commands.append("free -h")
            commands.append("df -h")
            explanation.extend(["العمليات", "الذاكرة", "المساحة"])

        else:
            commands.append("# وصف غير محدد")
            explanation.append("حاول وصف ما تريد بشكل أدق")

        self.call_count += 1
        return {
            "description": description,
            "os": os_type,
            "commands": commands,
            "explanation": explanation,
            "count": len(commands),
        }


# =========================
#  Skill Registry
# =========================

class ExtendedSkills:
    """مدير المهارات الموسعة"""
    def __init__(self):
        self.skills: Dict[str, SkillBase] = {}

    def register(self, skill: SkillBase):
        self.skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillBase]:
        return self.skills.get(name)

    def execute(self, name: str, **kwargs) -> Dict:
        skill = self.get(name)
        if not skill:
            return {"error": f"Skill '{name}' not found"}
        return skill.execute(**kwargs)

    def list(self) -> List[Dict]:
        return [s.info() for s in self.skills.values()]

    def count(self) -> int:
        return len(self.skills)


def register_all() -> ExtendedSkills:
    """تسجيل كل المهارات الموسعة"""
    mgr = ExtendedSkills()
    mgr.register(CodeGenerator())
    mgr.register(TextAnalyzer())
    mgr.register(TaskPlanner())
    mgr.register(DataReporter())
    mgr.register(CommandBuilder())
    return mgr


if __name__ == "__main__":
    manager = register_all()

    print("🧠 AHS Extended Skills")
    print(f"  Total: {manager.count()}\n")

    # اختبار CodeGenerator
    result = manager.execute("code_generator", description="للجمع", language="python")
    print(f"📝 CodeGen: {result['lines']} lines ({result['language']})")
    print(result['code'][:200])
    print()

    # اختبار TextAnalyzer
    text = "هذا منتج جيد جداً، أحببته كثيراً"
    result = manager.execute("text_analyzer", text=text, analysis_type="sentiment")
    print(f"📊 Sentiment: {result['sentiment']} (score: {result['sentiment_score']})")

    # اختبار TaskPlanner
    result = manager.execute("task_planner", task="اكتب كود Python")
    print(f"📋 Plan: {result['total_steps']} steps ({result['estimated_time']})")

    # اختبار CommandBuilder
    result = manager.execute("command_builder", description="docker ps")
    print(f"💻 Commands: {result['count']}")

    print("\n✅ Extended Skills ready")
