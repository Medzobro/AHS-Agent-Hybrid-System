# Changelog

## v0.2.0 (2026-05-07)

✨ **Major Release — 10,000+ lines**

### New Systems (15 modules)
- **Orchestrator** — Task classification (4 types + planning)
- **Orchestrator V2** — Multi-step flow orchestration
- **Agent Loop** — Complete agent execution loop
- **Hermes Bridge** — DeepSeek R1 communication
- **Tool Registry** — 10 built-in tools (calc, uuid, file ops, JSON)
- **Skill Manager** — Dynamic skill discovery & loading
- **Multi-Agent** — 5 agents with different roles in parallel
- **Event Bus** — Async communication between components
- **Config Manager** — Nested config with profiles & validation
- **Doctor** — 7 health checks (Hermes, API, filesystem, memory, network, Python env, performance)
- **Logger** — Full logging system with levels and file export
- **Monitor** — Real-time metrics, thresholds, and alerts
- **Scheduler** — Background task scheduling
- **Cache** — LRU cache with TTL and eviction
- **Pipeline** — Data processing pipelines
- **Plugin System** — Plugin discovery and lifecycle
- **Exporter** — Export to JSON, CSV, Markdown, HTML, Text
- **REPL** — Interactive command-line interface
- **Integration** — Unified entry point for all components
- **Utils** — Text, data, time, stats, file, security utilities

### Skills (10 skills)
- Code Generator — Generate code from natural language
- Text Analyzer — Sentiment, keywords, readability analysis
- Task Planner — Task breakdown and planning
- Data Reporter — Report generation
- Command Builder — Shell command construction
- Code Assistant — AI-powered code writing
- Code Review — Intelligent code review
- Research & Summarize — Deep research
- Project Planning — Project structure planning
- Learn New Skill — Self-learning capability

### Testing
- 18 comprehensive tests, all passing
- Coverage: Core, System, Skills, Integration, Performance, Utility

### Documentation
- Full Arabic guide (~450 lines)
- Full English guide (~400 lines)
- Comprehensive README
- Code comments in Arabic

### Performance
- Quick mode: <1s
- Hybrid mode: ~14s
- Code mode: ~21-27s (77-148 lines generated)
- Flow mode: ~10.5s (3+ steps)
- All 18 tests: ~28s

## v0.1.0 (2026-05-06)

- Initial release (~1,925 lines)
- Basic hybrid system: Orchestrator + Bridge + Agent Loop
- GitHub repository creation
- 3 demo scenarios
- CLI interface
