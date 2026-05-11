"""
AHS - Core Package
==================
The core engine — classification, planning, and agent loops.

Components:
  - orchestrator: Task classification and execution planning
  - orchestrator_v2: Multi-step flow orchestration
  - agent_loop: Complete agent loop (receive → execute → respond)

Supports:
  - 4 task types: QUICK, DEEP, CODE, COMMAND
  - Execution planning per type
  - Short-term learning memory
  - Hybrid Mode: OpenClaw + Hermes together

Usage:
  from core.orchestrator import HybridOrchestrator
  o = HybridOrchestrator()
  task_type, plan = o.classify_task("Write Python code")
"""

from .orchestrator import HybridOrchestrator, TaskType
from .agent_loop import HybridAgent

__all__ = [
    "HybridOrchestrator",
    "HybridOrchestratorV2",
    "HybridAgent",
    "TaskType",
]
