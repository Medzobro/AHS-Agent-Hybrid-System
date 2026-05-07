# 🤖 AHS - Agent Hybrid System

**OpenClaw + Hermes = Agent واحد هجين يجمع القوتين**

## 🎯 الرؤية
Agent ذكي واحد يجمع قدرات OpenClaw (تحكم، أوامر، تنفيذ سريع) مع قدرات Hermes (تفكير عميق، 85 مهارة، بحث، تحليل).

## 🧱 البنية

```
hybrid-agent/
├── main.py              # نقطة الدخول الرئيسية
├── core/
│   ├── orchestrator.py  # العقل المخطط — يصنف ويخطط المهام
│   └── agent_loop.py    # الحلقة الرئيسية — OpenClaw + Hermes
├── bridge/
│   ├── hermes_bridge.py # جسر Hermes مع DeepSeek R1
│   └── shared_memory.json # الذاكرة المشتركة
├── skills/
│   └── hybrid_skills.py # مهارات هجينة
├── tests/               # اختبارات
└── docs/                # توثيق
```

## 🚀 كيفية الاستخدام

### تشغيل سريع
```bash
python3 main.py "مهمتك هنا"
```

### وضع المحادثة
```bash
python3 main.py --interactive
```

### إظهار التفكير
```bash
python3 main.py "ابحث عن..." --thinking
```

### حالة النظام
```bash
python3 main.py --status
```

## 🧪 أمثلة

```bash
python3 main.py "من أنت"
python3 main.py "ابحث عن أفضل ممارسات AI Agents"
python3 main.py "خطط لمشروع نظام أتمتة ذكي"
```

## 🔄 آلية العمل

1. **تصنيف المهمة** — Orchestrator يحدد نوعها
2. **تخطيط** — من سينفذ ماذا (OpenClaw / Hermes / الإثنان)
3. **تنفيذ** — الخطوات تنفذ بالتسلسل
4. **ذاكرة مشتركة** — الدروس تحفظ للاستخدام المستقبلي

## 🧠 النموذج
- DeepSeek R1 (deepseek-reasoner) مع وضع التفكير
- Hermes v0.13.0 — 85 مهارة، 20 أداة
- OpenClaw — تحكم وتنفيذ سريع

## 📌 قادم
- [ ] Hybrid Skills إضافية
- [ ] واجهة Telegram
- [ ] Memory متطورة (RAG)
- [ ] Community على GitHub
- [ ] واجهة Web

---

**Project AHS — Agent Hybrid System** 🤝
