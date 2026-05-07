# AHS tests package
from ..__init__ import __version__
"""
AHS - Test Package
===================
اختبارات شاملة لجميع مكونات AHS.

الملفات:
  - test_suite.py: 18 اختباراً في 6 مجموعات:
    * Core (Orchestrator, Planning, AgentLoop, Errors)
    * System (Tools, Config, Doctor, MultiAgent, Skills)
    * Skills (Hybrid, CodeAssistant, Synthesizer)
    * Integration (Init, AutoMode)
    * Performance (JSON, Memory)
    * Utility (JSON tools, UUID)

التشغيل:
  python3 tests/test_suite.py

النتيجة المتوقعة:
  ✅ Passed: 18/18
  ❌ Failed: 0
"""
