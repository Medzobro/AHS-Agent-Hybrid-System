"""
AHS - System Package
=====================
Supporting systems — manage and organize everything.

Components (17):
  - config_manager: Configuration management (JSON, env, profiles)
  - doctor: Health checks (Hermes, API, filesystem, network)
  - event_system: Async event bus
  - integration: Integration layer — connects all components
  - logger: Full logging system
  - monitor: Performance and health monitoring
  - multi_agent: 5 agents with different roles in parallel
  - pipeline: Data processing pipelines
  - plugin_system: Plugin system
  - scheduler: Background task scheduling
  - skill_manager: Skill management and discovery
  - tool_registry: Tool registry (10 built-in tools)
  - cache: Smart caching
  - exporter: Data export (JSON, CSV, MD, HTML)
  - repl: Interactive command-line REPL
  - utils: Utilities (text, data, time)
  - AHSIntegration: Unified system entry point

Usage:
  from system.integration import AHSIntegration
  ahs = AHSIntegration()
  ahs.initialize()
  ahs.process("My task")
"""

from .config_manager import ConfigManager
from .doctor import Doctor
from .integration import AHSIntegration
from .logger import AHSLogger, LogLevel
from .multi_agent import AgentRole, AgentWorker, MultiAgentOrchestrator
from .skill_manager import SkillManager
from .tool_registry import ToolCategory, ToolRegistry, ToolResult, ToolSpec

__all__ = [
    "ConfigManager", "Doctor",
    "EventBus", "Event", "SystemEvents",
    "AHSIntegration",
    "AHSLogger", "LogLevel",
    "Monitor", "MetricsCollector",
    "MultiAgentOrchestrator", "AgentRole", "AgentWorker",
    "Plugin", "PluginManager", "PluginStatus",
    "SkillManager",
    "ToolRegistry", "ToolSpec", "ToolCategory", "ToolResult",
]
