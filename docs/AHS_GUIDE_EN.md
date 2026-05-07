# AHS Complete English Guide
## Agent Hybrid System — The Hybrid Intelligent Agent System

---

# Introduction

## What is AHS?

**AHS (Agent Hybrid System)** is a hybrid system combining two powerful AI agents:
1. **OpenClaw** — for control, execution, and fast responses
2. **Hermes** — for deep thinking with 85+ skills

Instead of choosing one, AHS selects the best approach for each task:
- Quick tasks → OpenClaw (under 1s)
- Deep tasks → Hermes (with DeepSeek R1 reasoning)
- Hybrid tasks → Both combined (11-14s)
- Code tasks → Hermes writes + OpenClaw saves

## Why AHS?

| Problem | AHS Solution |
|---------|-------------|
| Single AI agents are limited | AHS combines OpenClaw + Hermes into one system |
| No shared memory | Shared Memory + Event Bus connects all components |
| Hard to extend | Multi-Agent System with 5 different roles |
| No built-in tools | Tool Registry with 10 tools + extensible |
| No testing | Built-in suite with 18 tests |
| No plugins | Plugin System with auto-discovery |

## Architecture

```
AHS/
├── core/               # ◄ Core engine
│   ├── orchestrator.py      # Task classification & planning
│   ├── orchestrator_v2.py   # Multi-step flows
│   └── agent_loop.py        # Complete agent loop
├── bridge/             # ◄ Hermes bridge
│   └── hermes_bridge.py     # DeepSeek R1 communication
├── skills/             # ◄ Skills
│   ├── code_assistant.py    # Code assistant
│   ├── hybrid_skills.py     # Hybrid skills
│   ├── synthesizer.py       # Response synthesis
│   └── extended_skills.py   # Extended skill set
├── system/             # ◄ Systems
│   ├── config_manager.py    # Configuration management
│   ├── doctor.py            # Health checks
│   ├── event_system.py      # Event bus
│   ├── integration.py       # Integration layer
│   ├── logger.py            # Logging system
│   ├── monitor.py           # Monitoring
│   ├── multi_agent.py       # Multi-agent system
│   ├── pipeline.py          # Data pipelines
│   ├── plugin_system.py     # Plugin system
│   ├── scheduler.py         # Task scheduling
│   ├── skill_manager.py     # Skill management
│   ├── tool_registry.py     # Tool registry
│   ├── cache.py             # Caching system
│   ├── utils.py             # Utilities
│   └── repl.py              # Interactive REPL
├── tests/              # ◄ Tests
│   └── test_suite.py        # 18 comprehensive tests
├── docs/               # ◄ Documentation
│   ├── AHS_GUIDE.md         # Arabic guide
│   └── AHS_GUIDE_EN.md      # English guide (this file)
├── main.py             # ◄ CLI entry point
├── demo.py             # ◄ Demo scenarios
└── README.md           # ◄ Quick intro
```

---

# Installation

## Prerequisites

```bash
Python 3.10+
Hermes AI Agent (optional)
DeepSeek API key (or other provider)
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Medzobro/AHS-Agent-Hybrid-System.git
cd AHS-Agent-Hybrid-System

# 2. Run directly (no install)
python3 main.py --info

# 3. Test
python3 tests/test_suite.py
```

## Environment Variables

```bash
# DeepSeek API (for deep tasks)
export DEEPSEEK_API_KEY="sk-..."
export DEEPSEEK_MODEL="deepseek-reasoner"

# Hermes (optional — for advanced reasoning)
export HERMES_PATH="/path/to/hermes"
export HERMES_CONFIG="/path/to/config.yaml"
```

---

# Usage

## CLI

```bash
# Hybrid mode (default)
python3 main.py --hybrid "Write a Python calculator"

# Code mode
python3 main.py --code "Task management app"

# Multi-step flow
python3 main.py --flow

# System info
python3 main.py --info

# Interactive session
python3 main.py -i

# REPL
python3 system/repl.py
```

## Python API

```python
from system.integration import AHSIntegration

# Initialize
ahs = AHSIntegration()
ahs.initialize()

# Process task
result = ahs.process("What is AHS?", mode="hybrid")
print(result["response"])

# Get status
status = ahs.get_status()
print(f"✅ {status['components']}")

# Health check
health = ahs.health_check()
print(f"Health: {health['summary']}")
```

## Auto Mode

The system auto-selects the best mode:

| Task | Mode | Time |
|------|------|------|
| "Hello" | Quick | <1s |
| "What is AI?" | Hybrid | ~14s |
| "Write Python code" | Code | ~25s |
| Long task (200+ chars) | Flow | ~10s |

---

# Systems

## 1. Orchestrator

Classifies tasks automatically:

```python
from core.orchestrator import HybridOrchestrator

o = HybridOrchestrator()
task_type, plan = o.classify_task("write code")
# → TaskType.CODE
```

## 2. Tool Registry

10 built-in tools:

```python
from system.tool_registry import create_default_tools

tools = create_default_tools()
tools.list()  # all tools
result = tools.call("calculate", expression="2 + 2")
# → 4
```

## 3. Event Bus

Async communication between components:

```python
from system.event_system import EventBus, SystemEvents

bus = EventBus()
bus.on(SystemEvents.TASK_COMPLETED, my_handler)
bus.emit(SystemEvents.TASK_STARTED, {"task": "..."})
```

## 4. Multi-Agent System

5 agents working in parallel:

| Worker | Role | Skills |
|--------|------|--------|
| hermes-thinker | Deep reasoning | Analysis, planning |
| code-writer | Code generation | Programming |
| researcher | Research | Information gathering |
| code-critic | Code review | QA, best practices |
| skill-learner | Learning | New skill acquisition |

## 5. Data Pipeline

Structured data processing:

```python
from system.pipeline import build_text_pipeline

pipeline = build_text_pipeline()
result = pipeline.run("  <b>Raw data</b>  ")
# → cleaned and validated
```

## 6. Plugin System

Extend with external plugins:

```python
from system.plugin_system import PluginManager

mgr = PluginManager()
mgr.load_all()
mgr.enable("my_plugin")
```

## 7. Task Scheduler

Background scheduled tasks:

```python
from system.scheduler import Scheduler

scheduler = Scheduler()
scheduler.add_task("health_check", my_check, interval_seconds=3600)
scheduler.start()
```

## 8. Caching

Smart result caching:

```python
from system.cache import Cache

cache = Cache(max_size=200, default_ttl=300)
cache.set("key", "value")
value = cache.get("key")
```

## 9. Monitoring

Real-time system monitoring:

```python
from system.monitor import Monitor, DefaultThresholds

monitor = Monitor()
DefaultThresholds.apply(monitor)
monitor.record("api.response_time", 0.5)
```

---

# Skills

## Built-in Skills

1. **Code Generator** — Generate code from natural language descriptions
2. **Text Analyzer** — Analyze text (sentiment, keywords, readability)
3. **Task Planner** — Plan and break down tasks
4. **Data Reporter** — Generate reports from data
5. **Command Builder** — Build shell commands
6. **Code Assistant** — AI-powered code writing with file saving
7. **Research & Summarize** — Deep research and summarization
8. **Code Review** — Intelligent code review
9. **Project Planning** — Project structure and planning
10. **Learn New Skill** — Self-learning capability

---

# Testing

```bash
# Run all tests
python3 tests/test_suite.py

# Expected output:
# ✅ Passed: 18/18
# ❌ Failed: 0
```

Test coverage:
- **Core**: Orchestrator, Planning, AgentLoop, Error handling
- **System**: Tools, Config, Doctor, MultiAgent, Skills
- **Skills**: Hybrid, CodeAssistant, Synthesizer
- **Integration**: Init, AutoMode
- **Performance**: JSON, Memory
- **Utility**: JSON tools, UUID

---

# Design Philosophy

## Principles

1. **Hybrid first** — Don't choose between speed and depth, combine both
2. **Open source** — For all developers, in Arabic and English
3. **Extensible** — Plugins, skills, tools — everything is open
4. **Auto-intelligent** — System decides the best approach per task
5. **Reliable** — Tests, health checks, full logging

## Comparison

| Feature | AHS | AutoGPT | LangChain | CrewAI |
|---------|-----|---------|-----------|---------|
| Hybrid (fast + deep) | ✅ | ❌ | ❌ | ❌ |
| Arabic support | ✅ | ❌ | ❌ | ❌ |
| Multi-Agent | ✅ | ❌ | ❌ | ✅ |
| Open source | ✅ | ✅ | ✅ | ✅ |
| Under 500KB | ✅ | ❌ | ❌ | ❌ |
| Event System | ✅ | ❌ | ❌ | ❌ |
| Plugin System | ✅ | ❌ | ❌ | ❌ |
| Built-in tests | ✅ | ❌ | ❌ | ❌ |
| Auto mode | ✅ | ❌ | ❌ | ❌ |

---

# Development

## Add a New Skill

```python
# skills/my_skill.py
from system.skill_manager import Skill

class MySkill(Skill):
    def __init__(self):
        super().__init__("my_skill", "description")

    def execute(self, params):
        # Skill logic
        return "result"
```

## Add a New Tool

```python
from system.tool_registry import Tool, ToolCategory

tools.register(Tool(
    name="my_tool",
    category=ToolCategory.UTILITY,
    handler=lambda **kw: do_something(kw),
    description="Tool description",
))
```

## Add a Data Pipeline

```python
from system.pipeline import Pipeline

pipeline = Pipeline("my_pipeline")
pipeline.add_step("clean", clean_fn)
pipeline.add_step("analyze", analyze_fn)
```

## Add a Plugin

```python
from system.plugin_system import Plugin, PluginMeta

class MyPlugin(Plugin):
    meta = PluginMeta(
        name="my_plugin",
        version="1.0.0",
        description="My custom plugin",
    )

    def on_enable(self):
        super().on_enable()
        # Plugin activation code
```

---

# Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/amazing`
3. Write code + tests
4. Run tests: `python3 tests/test_suite.py`
5. Submit a Pull Request

---

# License

MIT License — free for use, modification, and distribution.

---

# Credits

- **Mohamed (@isgjobro)** — Project creator and maintainer
- **OpenClaw** — Primary agent platform
- **Hermes AI** — Deep thinking and skills
- **DeepSeek** — R1 reasoning model

---

> "One system combining the power of multiple agents"
> — AHS, v0.2.0
