"""
AHS - Skills Package
=====================
مجموعة المهارات الهجينة — تجمع بين OpenClaw (سريع) و Hermes (عميق).

المهارات:
  - code_assistant: مساعد برمجة — يكتب كوداً من الوصف بالعربية
  - hybrid_skills: 4 مهارات هجينة (بحث، مراجعة كود، تخطيط، تعلم)
  - synthesizer: دمج ردود OpenClaw + Hermes في رد واحد
  - extended_skills: مهارات إضافية (توليد كود، تحليل نصوص، تخطيط مهام)

مثال:
  from skills.hybrid_skills import HybridSkills
  skills = HybridSkills()
  result = skills.research_and_summarize("موضوع البحث")
"""

from .code_assistant import CodeAssistant
from .hybrid_skills import HybridSkills
from .synthesizer import ResponseSynthesizer
from .extended_skills import ExtendedSkills, SkillBase

__all__ = [
    "CodeAssistant",
    "HybridSkills",
    "ResponseSynthesizer",
    "ExtendedSkills",
    "SkillBase",
]
