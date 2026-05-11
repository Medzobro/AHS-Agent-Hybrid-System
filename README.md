# 🤝 AHS — Agent Hybrid System v1.0

**OpenClaw (TS) ⟷ Hermes (Python) عبر MCP**

نظام هجين يجمع OpenClaw (سريع، تحكم) + Hermes (ذكاء عميق) في نظام واحد.  
يتعامل مع المهام البسيطة فوراً، والمهام المعقدة يرسلها للذكاء العميق.

## 🚀 التشغيل السريع

### 1. عبر Python مباشر

```bash
# Service 1: MCP HTTP Bridge
python3 bridge/mcp_http_server.py

# Service 2: TypeScript Gateway
AHS_GATEWAY_PORT=18805 AHS_MCP_PORT=18900 node ts-core/dist/index.js
```

### 2. عبر Docker

```bash
docker compose up --build
```

### 3. عبر الطرفية — أمر واحد

```bash
cd hybrid-agent
make up
```

## 🧪 الاختبار

```bash
# Health check
curl http://localhost:18900/health
curl http://localhost:18805/health

# إرسال مهمة
curl -X POST http://localhost:18900/task \
  -H 'Content-Type: application/json' \
  -d '{"task":"قل: مرحبا","mode":"hybrid"}'

# Full Stack (TS → Python → Hermes)
curl -X POST http://localhost:18805/task \
  -H 'Content-Type: application/json' \
  -d '{"task":"Say: Hello from full stack"}'

# Web Search
curl -X POST http://localhost:18900/web_search \
  -H 'Content-Type: application/json' \
  -d '{"query":"AI agents 2026","count":3}'

# ذاكرة
curl -X POST http://localhost:18900/memory \
  -H 'Content-Type: application/json' \
  -d '{"action":"set","key":"my_note","value":"Hello World"}'

curl -X POST http://localhost:18900/memory \
  -H 'Content-Type: application/json' \
  -d '{"action":"get","key":"my_note"}'

# تنفيذ كود
curl -X POST http://localhost:18900/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"print(2+2)","lang":"python3"}'

# تقرير التعلم الذاتي
python3 -c "
import sys; sys.path.insert(0,'.')
from system.integration import AHSIntegration
a = AHSIntegration(); a.initialize()
r = a.learn_report()
print(f'Errors: {r[\"analyzer\"][\"total_errors_logged\"]}')
print(f'Fix rate: {r[\"analyzer\"][\"fix_rate\"]}%')
print(f'Improvements: {len(r.get(\"improvements\",[]))}')
"
```

## 📡 الـ Endpoints

| المسار | الطريقة | الوصف |
|--------|---------|-------|
| `/health` | GET | صحة النظام |
| `/task` | POST | إرسال مهمة لـ Hermes |
| `/execute` | POST | تنفيذ كود Python/Bash |
| `/web_search` | POST | بحث في الويب |
| `/memory` | POST | ذاكرة (get/set/delete) |
| `/memory/search` | POST | بحث في الذاكرة |
| `/memory/stats` | POST | إحصائيات الذاكرة |

## 🧠 Self-Learning

النظام يتعلم من أخطائه تلقائياً:

```python
from system.integration import AHSIntegration
ahs = AHSIntegration()
ahs.initialize()

# تقرير التعلم
print(ahs.learn_report())

# اقتراح تحسينات
for imp in ahs.suggest_improvements():
    print(imp)

# إصلاح تلقائي
ahs.auto_fix()
```

## 📁 هيكل المشروع

```
hybrid-agent/
├── bridge/
│   ├── mcp_http_server.py   ← MCP HTTP Bridge (18900)
│   ├── hermes_bridge.py      ← Hermes MCP v6 Bridge
│   ├── mcp_tools.py          ← Tool Registry
│   └── memory_store.py       ← SQLite Memory
├── system/
│   ├── self_learn.py         ← 🆕 Self-Learning
│   ├── tools.py              ← Web Search + Memory
│   ├── integration.py        ← 9/9 Components
│   └── doctor.py             ← Health Checks
├── ts-core/
│   └── dist/                 ← TypeScript Gateway (18805)
├── Dockerfile
├── docker-compose.yml
└── Makefile
```

## 🏗️ Stack

- **Front:** TypeScript (Node.js 22)
- **Back:** Python 3.13 (Hermes + MCP)
- **DB:** SQLite (Memory + Learning)
- **Deploy:** Docker + Docker Compose
- **Auth:** `.env` (DEEPSEEK_API_KEY)
- **Search:** DuckDuckGo (مجاني)

## 📜 License

MIT
