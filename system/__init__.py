"""
AHS - System Package
=====================
الأنظمة الداعمة — تدير وتنظم كل شيء.

المكونات (17):
  - config_manager: إدارة الإعدادات (JSON, env, profiles)
  - doctor: فحوصات صحية (Hermes, API, ملفات, شبكة)
  - event_system: ناقل الأحداث غير المتزامن
  - integration: طبقة التكامل — تربط كل المكونات
  - logger: نظام تسجيل متكامل
  - monitor: مراقبة الأداء والصحة
  - multi_agent: 5 وكلاء بأدوار مختلفة بالتوازي
  - pipeline: خطوط أنابيب البيانات
  - plugin_system: نظام الإضافات
  - scheduler: جدولة المهام التلقائية
  - skill_manager: إدارة المهارات واكتشافها
  - tool_registry: سجل الأدوات (10 أدوات مدمجة)
  - cache: تخزين مؤقت ذكي
  - exporter: تصدير البيانات (JSON, CSV, MD, HTML)
  - repl: واجهة تفاعلية سطرية
  - utils: أدوات مساعدة (نصوص، بيانات، وقت)
  - AHSIntegration: نقطة الدخول الموحدة للنظام

الاستخدام:
  from system.integration import AHSIntegration
  ahs = AHSIntegration()
  ahs.initialize()
  ahs.process("مهمتي")
"""

from .config_manager import ConfigManager
from .doctor import Doctor
from .event_system import EventBus, Event, SystemEvents
from .integration import AHSIntegration
from .logger import AHSLogger, LogLevel
from .monitor import Monitor, MetricsCollector
from .multi_agent import MultiAgentOrchestrator, AgentRole, AgentWorker
from .pipeline import Pipeline, PipelineRegistry
from .plugin_system import Plugin, PluginManager, PluginStatus
from .scheduler import Scheduler, ScheduledTask
from .skill_manager import SkillManager
from .tool_registry import ToolRegistry, Tool, ToolCategory

__all__ = [
    "ConfigManager", "Doctor",
    "EventBus", "Event", "SystemEvents",
    "AHSIntegration",
    "AHSLogger", "LogLevel",
    "Monitor", "MetricsCollector",
    "MultiAgentOrchestrator", "AgentRole", "AgentWorker",
    "Pipeline", "PipelineRegistry",
    "Plugin", "PluginManager", "PluginStatus",
    "Scheduler", "ScheduledTask",
    "SkillManager",
    "ToolRegistry", "Tool", "ToolCategory",
]
