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
-e 
## v0.4.0 (2026-05-11)

✨ **Parallel Release — TypeScript Core + Hermes MCP**

### TypeScript Core (جديد كلياً)
- **Gateway Server** — HTTP/WebSocket على port 18791/18792
- **AHEngine** — تصنيف ذكي (classify → plan → execute → respond)
- **Task Classifier** — تحليل المهام حسب الطول والكلمات المفتاحية
- **Plan Builder** — خطوات تنفيذ متعددة (حتى 5 مستويات)
- **Hermes Bridge (TS)** — عميل MCP v6 مع WebSocket + HTTP fallback

### Hermes MCP Bridge (مطوّر)
- **MCP Session Manager** — JSON-RPC 2.0 كامل مع مهلات واستثناءات
- **إعادة كتابة `hermes_bridge.py`** — قراءة API key من `.env`
- **CLI fallback** — إذا MCP مش متاح
- **Python AHSIntegration** — 8/8 components شغالة (init, quick, tools, doctor, multi-agent, memory)

### تحسينات
- **تنظيف system modules** — pipeline, exporter, scheduler, repl → archive
- **`.ahsrc`** — ملف إعدادات متحد
- **`.env`** — API keys محمية بـ `chmod 600`
- **`.gitignore`** — .env، __pycache__، node_modules
- **PLAN-v0.4.md** — خطة التطوير القادمة

### الـ 6 اختبارات السريعة
| الاختبار | الحالة |
|---------|--------|
| Init (8/8 components) | ✅ |
| Quick mode | ✅ |
| Tool Registry (10 tools) | ✅ |
| Doctor (7/7 checks) | ✅ |
| Multi-Agent (5 workers) | ✅ |
| Shared Memory | ✅ |

### البنية الجديدة
```
hybrid-agent/
├── ts-core/          # TypeScript Core (جديد)
│   ├── src/
│   │   ├── index.ts          # المدخل الرئيسي
│   │   ├── gateway.ts        # HTTP/WS Gateway
│   │   ├── agent-loop.ts     # Agent Loop
│   │   ├── hermes-bridge.ts  # MCP Client
│   │   ├── orchestrator/     # AI تصنيف + تخطيط
│   │   └── types/            # أنواع مركزية
│   └── dist/                 # JS مترجم
├── bridge/           # Python Bridge
├── core/             # Python Core
├── system/           # System Modules
├── skills/           # Skills
├── tests/            # tests
└── .ahsrc            # إعدادات مشتركة
```
