"""
AHS - Bridge Package
=====================
جسر التواصل مع Hermes AI Agent للتفكير العميق.

المكونات:
  - hermes_bridge: اتصال مع Hermes عبر CLI أو API

يدعم:
  - DeepSeek R1 (deepseek-reasoner) مع reasoning_content
  - OpenRouter (أي نموذج متاح)
  - استخراج الرد من أحدث session
  - Shared Memory للتنسيق

الاستخدام:
  from bridge.hermes_bridge import HermesBridge
  bridge = HermesBridge()
  result = bridge.send_task("ما هو الذكاء الاصطناعي؟")
"""

from .hermes_bridge import HermesBridge

__all__ = ["HermesBridge"]
