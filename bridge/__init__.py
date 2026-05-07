"""
AHS - Bridge Package
=====================
Communication bridge with Hermes AI Agent for deep reasoning.

Components:
  - hermes_bridge: Connects to Hermes via CLI or API

Supports:
  - DeepSeek R1 (deepseek-reasoner) with reasoning_content
  - OpenRouter (any available model)
  - Latest session response extraction
  - Shared Memory for coordination

Usage:
  from bridge.hermes_bridge import HermesBridge
  bridge = HermesBridge()
  result = bridge.send_task("What is artificial intelligence?")
"""

from .hermes_bridge import HermesBridge

__all__ = ["HermesBridge"]
