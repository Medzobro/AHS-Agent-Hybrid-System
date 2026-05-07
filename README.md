# 🤝 AHS - Agent Hybrid System

[![Version](https://img.shields.io/badge/version-0.2.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Python](https://img.shields.io/badge/python-3.10+-orange)]()
[![Tests](https://img.shields.io/badge/tests-18/18-✅)]()
[![Lines](https://img.shields.io/badge/lines-10K+-success)]()

**نظام هجين يجمع OpenClaw (تحكم سريع) + Hermes (تفكير عميق DeepSeek R1).**

AHS هو نظام وكيل ذكاء اصطناعي هجين يجمع قوة وكلاء متعددين في نظام واحد متكامل. بدلاً من اختيار وكيل واحد، AHS يختار الأسلوب الأمثل لكل مهمة — سريع للمهام البسيطة، وعميق للمهام المعقدة.

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

| الميزة | الحالة |
|--------|--------|
| 🧠 **Hybrid Mode** — OpenClaw سريع + Hermes عميق | ✅ |
| 🔄 **Auto Mode** — اختيار الوضع الأنسب تلقائياً | ✅ |
| 🏗️ **Multi-Agent** — 5 وكلاء بأدوار مختلفة | ✅ |
| 🔧 **Tool Registry** — 10 أدوات مدمجة | ✅ |
| 🧩 **Plugin System** — إضافات خارجية | ✅ |
| 📊 **Monitoring** — مراقبة الأداء والصحة | ✅ |
| ⏰ **Scheduler** — مهام تلقائية في الخلفية | ✅ |
| 📝 **Logger** — تسجيل كامل لكل شيء | ✅ |
| 📡 **Event Bus** — تواصل غير متزامن بين المكونات | ✅ |
| 🧪 **Tests** — 18 اختبار شامل | ✅ |
| 💾 **Cache** — تخزين مؤقت ذكي | ✅ |
| 📤 **Exporter** — تصدير JSON, CSV, MD, HTML | ✅ |
| 💬 **REPL** — واجهة تفاعلية سطرية | ✅ |
| 🌐 **Data Pipeline** — خطوط معالجة بيانات | ✅ |
| 🏥 **Doctor** — فحوصات صحية للنظام | ✅ |

## 📊 Performance

| Mode | Time | Use Case |
|------|------|----------|
| **Quick** | <1s | ترحيب، أوامر بسيطة |
| **Hybrid** | ~14s | أسئلة معرفية، تحليل |
| **Code** | ~21-27s | كتابة كود |
| **Flow** | ~10s | مهام متعددة الخطوات |
| **Deep** | ~20-30s | بحث عميق |

## 🏗️ Architecture (10,000+ lines)

```
AHS/
├── core/           # 4 files  ← التصنيف والتخطيط
├── bridge/         # 1 file   ← جسر Hermes
├── skills/         # 5 files  ← المهارات (10 مهارات)
├── system/         # 15 files ← الأنظمة (كل شيء)
├── tests/          # 1 file   ← 18 اختبار
├── docs/           # 2 files  ← دليل عربي + إنجليزي
├── generated/      # 2 files  ← كود مولّد
└── 34 ملفاً إجمالاً
```

## 🔧 Systems

| النظام | الوصف | الملفات |
|--------|-------|---------|
| **Orchestrator** | تصنيف المهام وتخطيطها | 2 |
| **Agent Loop** | حلقة الوكيل الكاملة | 1 |
| **Hermes Bridge** | التواصل مع DeepSeek R1 | 1 |
| **Tool Registry** | 10 أدوات قابلة للتوسع | 1 |
| **Skill Manager** | اكتشاف وتحميل المهارات | 1 |
| **Multi-Agent** | 5 وكلاء بالتوازي | 1 |
| **Event Bus** | تواصل غير متزامن | 1 |
| **Config Manager** | إعدادات متداخلة مع Profiles | 1 |
| **Logger** | تسجيل كامل بملفات | 1 |
| **Monitor** | مراقبة وتنبيهات | 1 |
| **Scheduler** | مهام تلقائية | 1 |
| **Cache** | تخزين مؤقت LRU | 1 |
| **Pipeline** | خطوط معالجة بيانات | 1 |
| **Plugin System** | إضافات خارجية | 1 |
| **Exporter** | تصدير 5 صيغ | 1 |
| **REPL** | واجهة تفاعلية | 1 |
| **Doctor** | فحوصات صحية | 1 |
| **Integration** | نقطة دخول موحدة | 1 |
| **Utils** | أدوات مساعدة | 1 |

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

- **Arabic**: `docs/AHS_GUIDE.md` — الدليل العربي الكامل
- **English**: `docs/AHS_GUIDE_EN.md` — Full English guide
- **Code**: `docs/` مع شروحات لكل ملف

## 🤝 Contributing

نرحب بمساهماتكم! المشروع مفتوح المصدر للجميع.

```bash
python3 tests/test_suite.py    # تشغيل الاختبارات
git checkout -b feature/amazing  # إنشاء فرع
# ... كتابة الكود ...
git commit -m "إضافة رائعة"
git push origin feature/amazing
# إنشاء Pull Request
```

## 📜 License

**MIT License** — حر بالكامل للاستخدام والتعديل والنشر.

## 👤 Credits

- **Mohamed (@isgjobro)** — صاحب الفكرة والمطور الرئيسي
- **OpenClaw** — منصة الوكيل الرئيسية
- **Hermes AI** — التفكير العميق والمهارات
- **DeepSeek** — نموذج R1

---

> **10,000+ سطر كود | 34 ملف | 15 نظام | 10 مهارات | 18 اختبار**
>
> "نظام واحد يجمع قوة وكلاء متعددين" 🤝

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
