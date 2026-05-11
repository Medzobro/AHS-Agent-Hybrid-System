"""
AHS - Skills Package
=====================
Hybrid skills collection — combining OpenClaw (fast) + Hermes (deep).

Skills:
  - code_assistant: Programming assistant — generates code from natural language
  - hybrid_skills: 4 hybrid skills (research, code review, planning, learning)
  - synthesizer: Merges OpenClaw + Hermes responses into one
  - extended_skills: Additional skills (code gen, text analysis, task planning)

Example:
  from skills.hybrid_skills import HybridSkills
  skills = HybridSkills()
  result = skills.research_and_summarize("Research topic")
"""

from .code_assistant import CodeAssistant
from .extended_skills import ExtendedSkills, SkillBase
from .hybrid_skills import HybridSkills
from .synthesizer import ResponseSynthesizer

__all__ = [
    "CodeAssistant",
    "HybridSkills",
    "ResponseSynthesizer",
    "ExtendedSkills",
    "SkillBase",
]
