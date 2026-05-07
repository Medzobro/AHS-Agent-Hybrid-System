# 🤝 AHS - Agent Hybrid System

[![Version](https://img.shields.io/badge/version-0.2.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Python](https://img.shields.io/badge/python-3.10+-orange)]()
[![Tests](https://img.shields.io/badge/tests-18/18-✅)]()
[![Lines](https://img.shields.io/badge/lines-10K+-success)]()

**A hybrid system combining OpenClaw (fast control) + Hermes (deep reasoning via DeepSeek R1).**

AHS is a hybrid AI agent system that combines the power of multiple agents into one integrated platform. Instead of choosing a single agent, AHS selects the optimal approach for each task — fast for simple tasks, deep for complex ones.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Medzobro/AHS-Agent-Hybrid-System.git
cd AHS-Agent-Hybrid-System

# System info
python3 main.py --info

# Run all tests
python3 tests/test_suite.py

# Interactive mode
python3 system/repl.py
```

## ✨ Features

| Feature | Status |
|---------|--------|
| 🧠 **Hybrid Mode** — OpenClaw fast + Hermes deep reasoning | ✅ |
| 🔄 **Auto Mode** — Auto-selects best execution mode | ✅ |
| 🏗️ **Multi-Agent** — 5 agents with different roles in parallel | ✅ |
| 🔧 **Tool Registry** — 10 built-in extensible tools | ✅ |
| 🧩 **Plugin System** — External plugin discovery & loading | ✅ |
| 📊 **Monitoring** — Real-time performance & health monitoring | ✅ |
| ⏰ **Scheduler** — Background task scheduling (cron-like) | ✅ |
| 📝 **Logger** — Full logging with files, memory, levels | ✅ |
| 📡 **Event Bus** — Async pub/sub communication between components | ✅ |
| 🧪 **Tests** — 18 comprehensive tests, all passing | ✅ |
| 💾 **Cache** — Smart LRU cache with TTL expiration | ✅ |
| 📤 **Exporter** — Export to JSON, CSV, Markdown, HTML | ✅ |
| 💬 **REPL** — Interactive command-line interface | ✅ |
| 🌐 **Data Pipeline** — Configurable data processing pipelines | ✅ |
| 🏥 **Doctor** — 7 health checks (Hermes, API, FS, network, memory, Python, perf) | ✅ |

## 📊 Performance

| Mode | Time | Use Case |
|------|------|----------|
| **Quick** | <1s | Greetings, simple commands |
| **Hybrid** | ~14s | Knowledge questions, analysis |
| **Code** | ~21-27s | Code generation |
| **Flow** | ~10s | Multi-step workflows |
| **Deep** | ~20-30s | Deep research |

## 🏗️ Architecture (10,000+ lines)

```
AHS/
├── core/           # 4 files  — Task classification & planning
├── bridge/         # 1 file   — Hermes bridge
├── skills/         # 5 files  — 10 hybrid skills
├── system/         # 15 files — All support systems
├── tests/          # 1 file   — 18 tests
├── docs/           # 2 files  — Arabic + English guides
├── generated/      # 2 files  — AI-generated code
└── 34 files total
```

## 🔧 Systems

| System | Description | Files |
|--------|-------------|-------|
| **Orchestrator** | Task classification & planning | 2 |
| **Agent Loop** | Full agent execution loop | 1 |
| **Hermes Bridge** | DeepSeek R1 communication bridge | 1 |
| **Tool Registry** | 10 extensible tools with rate limiting | 1 |
| **Skill Manager** | Dynamic skill discovery & loading | 1 |
| **Multi-Agent** | 5 parallel agents with distinct roles | 1 |
| **Event Bus** | Async pub/sub event system | 1 |
| **Config Manager** | Nested config with profiles | 1 |
| **Logger** | Full file/memory logging with levels | 1 |
| **Monitor** | Real-time metrics & alerts | 1 |
| **Scheduler** | Background recurring tasks | 1 |
| **Cache** | LRU cache with TTL | 1 |
| **Pipeline** | Data processing pipelines | 1 |
| **Plugin System** | External plugin discovery | 1 |
| **Exporter** | JSON, CSV, MD, HTML export | 1 |
| **REPL** | Interactive command-line shell | 1 |
| **Doctor** | 7 health checks | 1 |
| **Integration** | Unified entry point | 1 |
| **Utils** | Text, data, time, file utilities | 1 |

## 🧪 Tests (18/18 ✅)

```
Core Components     → 4/4 ✅
System Components   → 5/5 ✅
Skills              → 3/3 ✅
Integration         → 2/2 ✅
Performance         → 2/2 ✅
Utility             → 2/2 ✅
```

## 📚 Documentation

- **Arabic**: `docs/AHS_GUIDE.md` — Full Arabic guide
- **English**: `docs/AHS_GUIDE_EN.md` — Full English guide
- **Code**: `docs/` with inline explanations for every file

## 🤝 Contributing

We welcome contributions! This is an open-source project for everyone.

```bash
python3 tests/test_suite.py    # Run tests
git checkout -b feature/amazing  # Create feature branch
# ... write your code ...
git commit -m "Add amazing feature"
git push origin feature/amazing
# Create Pull Request
```

## 📜 License

**MIT License** — Free to use, modify, and distribute.

## 👤 Credits

- **Mohamed (@isgjobro)** — Creator and lead developer
- **OpenClaw** — Primary agent platform
- **Hermes AI** — Deep reasoning and skills
- **DeepSeek** — R1 reasoning model

---

> **10,000+ lines | 34 files | 15 systems | 10 skills | 18 tests**
>
> "One system combining the power of multiple agents" 🤝

## Directory Structure

```
AHS-Agent-Hybrid-System/
│
├── core/                     # Core engine
│   ├── __init__.py
│   ├── agent_loop.py         # Agent execution loop
│   ├── orchestrator.py       # Task classification & planning
│   └── orchestrator_v2.py    # Multi-step flow orchestrator
│
├── bridge/                   # Hermes communication
│   ├── __init__.py
│   └── hermes_bridge.py      # DeepSeek R1 bridge
│
├── skills/                   # Hybrid skills
│   ├── __init__.py
│   ├── code_assistant.py     # AI code writing
│   ├── extended_skills.py    # 5 extended skills
│   ├── hybrid_skills.py      # 4 hybrid skills
│   └── synthesizer.py        # Response synthesis
│
├── system/                   # Supporting systems
│   ├── __init__.py
│   ├── cache.py              # LRU caching
│   ├── config_manager.py     # Configuration
│   ├── doctor.py             # Health checks
│   ├── event_system.py       # Event bus
│   ├── exporter.py           # Data export
│   ├── integration.py        # Unified entry point
│   ├── logger.py             # Logging system
│   ├── monitor.py            # Monitoring
│   ├── multi_agent.py        # Multi-agent system
│   ├── pipeline.py           # Data pipelines
│   ├── plugin_system.py      # Plugin system
│   ├── repl.py               # Interactive REPL
│   ├── scheduler.py          # Task scheduler
│   ├── skill_manager.py      # Skill management
│   ├── tool_registry.py      # Tool registry
│   └── utils.py              # Utilities
│
├── tests/                    # Tests
│   ├── __init__.py
│   └── test_suite.py         # 18 tests
│
├── docs/                     # Documentation
│   ├── AHS_GUIDE.md          # Arabic guide
│   └── AHS_GUIDE_EN.md       # English guide
│
├── generated/                # Generated code
│   ├── __init__.py
│   └── *.py                  # AI-generated files
│
├── main.py                   # CLI entry point
├── demo.py                   # Demo scenarios
├── README.md                 # This file
└── CHANGELOG.md              # Version history
```

## Quick Reference

```bash
# Help
python3 main.py --help

# System info
python3 main.py --info

# Process a task
python3 main.py --hybrid "Your task here"

# Generate code
python3 main.py --code "Write a Python function"

# Run all tests
python3 tests/test_suite.py

# Interactive REPL
python3 system/repl.py
```
