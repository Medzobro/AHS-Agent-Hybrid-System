# دليل AHS الكامل
## Agent Hybrid System — النظام الهجين للوكلاء الأذكياء

---

# المقدمة

## ما هو AHS؟

**AHS (Agent Hybrid System)** هو نظام هجين يجمع بين قوتين:
1. **OpenClaw** — للتحكم والتنفيذ والردود السريعة
2. **Hermes** — للتفكير العميق باستخدام 85+ مهارة

بدلاً من اختيار واحد منهما، AHS يختار الأفضل لكل مهمة:
- مهام سريعة → OpenClaw (خلال ثانية)
- مهام عميقة → Hermes (مع تفكير DeepSeek R1)
- مهام هجينة → الاثنان معاً (11-14 ثانية)
- مهام برمجية → Hermes يكتب + OpenClaw يحفظ

## لماذا AHS؟

| المشكلة | الحل في AHS |
|---------|------------|
| وكلاء AI منفردون محدودون | AHS يجمع OpenClaw + Hermes في نظام واحد |
| لا توجد ذاكرة مشتركة | Shared Memory + Event Bus يربط كل المكونات |
| صعوبة التوسع | Multi-Agent System مع 5 أدوار مختلفة |
| لا أدوات مدمجة | Tool Registry مع 10 أدوات + إمكانية الإضافة |
| لا اختبارات | Suite مدمجة مع 18 اختبار |
| لا إضافات | Plugin System مع اكتشاف تلقائي |

## المكونات الرئيسية

```
AHS/
├── core/               # ◄ النواة الأساسية
│   ├── orchestrator.py      # تصنيف المهام وتخطيطها
│   ├── orchestrator_v2.py   # تدفق متعدد الخطوات
│   └── agent_loop.py        # حلقة الوكيل الكاملة
├── bridge/             # ◄ جسر Hermes
│   └── hermes_bridge.py     # اتصال DeepSeek R1
├── skills/             # ◄ المهارات
│   ├── code_assistant.py    # مساعد برمجة
│   ├── hybrid_skills.py     # مهارات هجينة
│   └── synthesizer.py       # دمج الردود
├── system/             # ◄ الأنظمة
│   ├── config_manager.py    # إدارة الإعدادات
│   ├── doctor.py            # فحوصات صحية
│   ├── event_system.py      # ناقل الأحداث
│   ├── integration.py       # طبقة التكامل
│   ├── logger.py            # نظام التسجيل
│   ├── multi_agent.py       # وكلاء متعددون
│   ├── pipeline.py          # خطوط بيانات
│   ├── plugin_system.py     # نظام الإضافات
│   ├── scheduler.py         # جدولة المهام
│   ├── skill_manager.py     # إدارة المهارات
│   ├── tool_registry.py     # سجل الأدوات
│   └── utils.py             # أدوات مساعدة
├── tests/              # ◄ الاختبارات
│   └── test_suite.py        # 18 اختبار شامل
├── main.py             # ◄ نقطة الدخول CLI
├── demo.py             # ◄ سيناريوهات تجريبية
└── README.md           # ◄ هذا الملف
```

---

# التركيب (Installation)

## المتطلبات

```bash
Python 3.10+
Hermes AI Agent (اختياري)
DeepSeek API key (أو أي provider آخر)
```

## التثبيت السريع

```bash
# 1. استنساخ المشروع
git clone https://github.com/Medzobro/AHS-Agent-Hybrid-System.git
cd AHS-Agent-Hybrid-System

# 2. تشغيل مباشر (بدون تثبيت)
python3 main.py --info

# 3. اختبار
python3 tests/test_suite.py
```

## متغيرات البيئة

```bash
# DeepSeek API (للمهام العميقة)
export DEEPSEEK_API_KEY="sk-..."
export DEEPSEEK_MODEL="deepseek-reasoner"

# Hermes (اختياري — للتفكير العميق)
export HERMES_PATH="/path/to/hermes"
export HERMES_CONFIG="/path/to/config.yaml"
```

---

# الاستخدام (Usage)

## سطر الأوامر

```bash
# وضع هجين (افتراضي)
python3 main.py --hybrid "اكتب كود Python لجمع رقمين"

# وضع برمجي
python3 main.py --code "برنامج لإدارة المهام"

# تدفق متعدد الخطوات
python3 main.py --flow

# معلومات النظام
python3 main.py --info

# جلسة تفاعلية
python3 main.py -i
```

## كلغة برمجة (Python API)

```python
from system.integration import AHSIntegration

# تهيئة
ahs = AHSIntegration()
ahs.initialize()

# معالجة مهمة
result = ahs.process("ما هو AHS؟", mode="hybrid")
print(result["response"])

# فحص صحي
status = ahs.get_status()
print(f"✅ {status['components']}")

# فحص طبي
health = ahs.health_check()
print(f"Health: {health['summary']}")
```

## الوضع التلقائي (Auto Mode)

النظام يختار الوضع الأنسب تلقائياً:

| المهمة | الوضع | الزمن |
|--------|-------|-------|
| "مرحبا" | Quick | <1s |
| "ما هو الذكاء الاصطناعي؟" | Hybrid | ~14s |
| "اكتب كود بايثون" | Code | ~25s |
| نص طويل (200+ حرف) | Flow | ~10s |

---

# الأنظمة (Systems)

## 1. Orchestrator — المخطط الذكي

يصنف المهام تلقائياً:

```python
from core.orchestrator import HybridOrchestrator

o = HybridOrchestrator()
task_type, plan = o.classify_task("اكتب كود")
# → TaskType.CODE
```

## 2. Tool Registry — سجل الأدوات

10 أدوات مدمجة:

```python
from system.tool_registry import create_default_tools

tools = create_default_tools()
tools.list()  # جميع الأدوات
result = tools.call("calculate", expression="2 + 2")
# → 4
```

## 3. Event Bus — ناقل الأحداث

تواصل غير متزامن بين المكونات:

```python
from system.event_system import EventBus, SystemEvents

bus = EventBus()
bus.on(SystemEvents.TASK_COMPLETED, my_handler)
bus.emit(SystemEvents.TASK_STARTED, {"task": "..."})
```

## 4. Multi-Agent — وكلاء متعددون

5 أدوار مختلفة تعمل بالتوازي:

| العامل | الدور | المهارات |
|--------|-------|---------|
| hermes-thinker | التفكير العميق | تحليل، تخطيط |
| code-writer | كتابة الكود | برمجة |
| researcher | البحث | معلومات |
| code-critic | مراجعة الكود | QA |
| skill-learner | التعلم | مهارات جديدة |

## 5. Pipeline — خطوط البيانات

معالجة منظمة للبيانات:

```python
from system.pipeline import build_text_pipeline

pipeline = build_text_pipeline()
result = pipeline.run("  <b>بيانات</b>  ")
# → cleaned and validated
```

## 6. Plugin System — الإضافات

توسيع النظام بإضافات خارجية:

```python
from system.plugin_system import PluginManager

mgr = PluginManager()
mgr.load_all()
mgr.enable("my_plugin")
```

## 7. Scheduler — الجدولة

مهام تلقائية في الخلفية:

```python
from system.scheduler import Scheduler

scheduler = Scheduler()
scheduler.add_task("check_health", my_check, interval_seconds=3600)
scheduler.start()
```

---

# المهارات (Skills)

## المهارات الهجينة

4 مهارات هجينة جاهزة:

1. **research_and_summarize** — بحث + تلخيص عميق
2. **code_review** — مراجعة الكود بذكاء
3. **plan_project** — تخطيط المشاريع
4. **learn_new_skill** — تعلم مهارات جديدة

## Code Assistant

مساعد برمجة ذكي:
- يكتب كوداً جاهزاً
- يحفظ الملفات تلقائياً
- يدعم: Python, JavaScript, Bash, HTML

## Response Synthesizer

يدمج ردود OpenClaw (سريعة) + Hermes (عميقة) في رد واحد متكامل.

---

# الاختبارات (Tests)

```bash
# تشغيل كل الاختبارات
python3 tests/test_suite.py

# النتيجة المتوقعة:
# ✅ Passed: 18/18
# ❌ Failed: 0
```

ماذا يختبر:
- Core: Orchestrator, Planning, AgentLoop, Errors
- System: Tools, Config, Doctor, MultiAgent, Skills
- Skills: Hybrid, CodeAssistant, Synthesizer
- Integration: Init, AutoMode
- Performance: JSON, Memory
- Utility: JSON tools, UUID

---

# فلسفة التصميم

## المبادئ

1. **الهجين أولاً** — لا نختار بين السرعة والعمق، نجمع الاثنين
2. **مفتوح المصدر** — لكل المطورين، بالعربية والإنجليزية
3. **قابل للتوسع** — إضافات، مهارات، أدوات — كل شيء مفتوح
4. **ذكي تلقائياً** — النظام يقرر أفضل طريقة لكل مهمة
5. **موثوق** — اختبارات، فحوصات صحية، تسجيل كامل

## مقارنة مع الأنظمة الأخرى

| الميزة | AHS | Agents | AutoGPT | LangChain |
|--------|-----|--------|---------|-----------|
| هجين (سريع + عميق) | ✅ | ❌ | ❌ | ❌ |
| عربي | ✅ | ❌ | ❌ | ❌ |
| Multi-Agent | ✅ | ✅ | ❌ | ❌ |
| مفتوح المصدر | ✅ | ✅ | ✅ | ✅ |
| <500KB | ✅ | ❌ | ❌ | ❌ |
| Event System | ✅ | ❌ | ❌ | ❌ |
| Plugin System | ✅ | ❌ | ❌ | ❌ |
| اختبارات مدمجة | ✅ | ❌ | ❌ | ❌ |

---

# التطوير (Development)

## إضافة مهارة جديدة

```python
# skills/my_skill.py
from system.skill_manager import Skill

class MySkill(Skill):
    def __init__(self):
        super().__init__("my_skill", "وصف المهارة")

    def execute(self, params):
        # كود المهارة
        return "نتيجة"
```

## إضافة أداة جديدة

```python
from system.tool_registry import Tool, ToolCategory

tools.register(Tool(
    name="my_tool",
    category=ToolCategory.UTILITY,
    handler=lambda **kw: do_something(kw),
    description="شرح الأداة",
))
```

## إضافة Pipeline

```python
from system.pipeline import Pipeline

my_pipeline = Pipeline("my_pipeline")
my_pipeline.add_step("clean", clean_fn)
my_pipeline.add_step("analyze", analyze_fn)
```

---

# المساهمة (Contributing)

1. استنساخ المشروع
2. إنشاء فرع: `git checkout -b feature/amazing`
3. كتابة الكود + اختبارات
4. تشغيل الاختبارات: `python3 tests/test_suite.py`
5. رفع الفرع وإنشاء Pull Request

---

# الترخيص (License)

MIT License — حر بالكامل للاستخدام والتعديل والنشر.

---

# الشكر (Credits)

- **Mohamed (@isgjobro)** — صاحب الفكرة والمشروع
- **OpenClaw** — منصة الوكيل الرئيسية
- **Hermes AI** — التفكير العميق والمهارات
- **DeepSeek** — نموذج R1 الرائع

---

> "نظام واحد يجمع قوة وكلاء متعددين"
> — AHS, v0.2.0
