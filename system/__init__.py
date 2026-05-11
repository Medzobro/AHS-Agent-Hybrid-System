"""
AHS - System Package
=====================
Supporting systems — v1.0 (cleaned, no dead modules).

Available:
  - integration: Main entry point — connects HermesBridge + ToolRegistry + SkillManager
  - skill_manager: Skill management
  - tool_registry: 8+ built-in tools
  - self_learn: Error analysis and auto-fix
"""

from .integration import AHSIntegration, bootstrap
from .self_learn import SelfLearningSystem
from .skill_manager import SkillManager
from .tool_registry import ToolCategory, ToolRegistry, ToolResult, ToolSpec

__all__ = [
    "AHSIntegration", "bootstrap",
    "SelfLearningSystem",
    "SkillManager",
    "ToolRegistry", "ToolSpec", "ToolCategory", "ToolResult",
]
