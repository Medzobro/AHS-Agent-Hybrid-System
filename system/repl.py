#!/usr/bin/env python3
"""
AHS - REPL (Read-Eval-Print Loop)
===================================
واجهة تفاعلية سطرية للتفاعل مع AHS.

المميزات:
  - جلسة تفاعلية كاملة
  - أوامر مدمجة (/help, /status, /health, /tools...)
  - تصدير الجلسة
  - سجل الأوامر
  - إكمال تلقائي للأوامر
"""

import json, os, sys, time, cmd, readline, shlex
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class AHSREPL(cmd.Cmd):
    """
    واجهة تفاعلية سطرية للنظام.
    """

    intro = """
╔══════════════════════════════════════════╗
║  🤝 AHS - Agent Hybrid System v0.2.0    ║
║  اكتب help أو /help للأوامر              ║
║  اكتب /quit أو Ctrl+C للخروج             ║
╚══════════════════════════════════════════╝
"""
    prompt = "🤝 AHS> "

    def __init__(self, ahs=None):
        super().__init__()
        self.ahs = ahs
        self.session_log: List[Dict] = []
        self.mode = "auto"
        self.verbose = False
        self.start_time = time.time()

    def default(self, line: str):
        """معالجة أي إدخال غير معروف"""
        if not line.strip():
            return

        # أوامر النظام
        if line.startswith("/"):
            self._handle_system_command(line[1:])
            return

        # معالجة المهمة
        self._process_task(line)

    def _handle_system_command(self, cmd_line: str):
        parts = shlex.split(cmd_line)
        cmd = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        commands = {
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
            "status": self._cmd_status,
            "health": self._cmd_health,
            "tools": self._cmd_tools,
            "skills": self._cmd_skills,
            "mode": self._cmd_mode,
            "history": self._cmd_history,
            "stats": self._cmd_stats,
            "clear": self._cmd_clear,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "verbose": self._cmd_verbose,
            "version": self._cmd_version,
            "export": self._cmd_export,
            "doctor": self._cmd_doctor,
            "config": self._cmd_config,
            "pipeline": self._cmd_pipeline,
            "events": self._cmd_events,
            "plugins": self._cmd_plugins,
            "scheduler": self._cmd_scheduler,
        }

        handler = commands.get(cmd)
        if handler:
            handler(*args)
        else:
            print(f"❌ أمر غير معروف: /{cmd}")
            print("   اكتب /help لعرض الأوامر المتاحة")

    def _cmd_help(self, *args):
        """عرض المساعدة"""
        help_text = """
📋 أوامر AHS:

  /help              ← عرض هذه المساعدة
  /quit, /exit       ← الخروج

  /status            ← حالة النظام
  /health            ← فحص صحي كامل
  /doctor            ← تشخيص مفصل
  /stats             ← إحصائيات
  /version           ← الإصدار

  /mode [auto|hybrid|quick|deep|code|flow]  ← تغيير الوضع
  /verbose           ← تفعيل/تعطيل العرض المفصل

  /tools             ← عرض الأدوات المتاحة
  /skills            ← عرض المهارات
  /config            ← عرض الإعدادات
  /plugins           ← عرض الإضافات
  /pipeline          ← عرض خطوط البيانات
  /events            ← عرض الأحداث
  /scheduler         ← عرض المهام المجدولة

  /history           ← سجل الأوامر
  /clear             ← مسح الشاشة
  /save [filename]   ← حفظ الجلسة
  /load [filename]   ← تحميل جلسة
  /export [filename] ← تصدير السجل

الوضع الحالي: {mode}

أمثلة:
  🤝 AHS> ما هو AHS؟
  🤝 AHS> اكتب كود Python
  🤝 AHS> /mode deep
  🤝 AHS> /health
""".format(mode=self.mode)
        print(help_text)

    def _cmd_quit(self, *args):
        """الخروج من النظام"""
        print("👋 مع السلامة!")
        return True

    def _cmd_status(self, *args):
        """عرض حالة النظام"""
        if not self.ahs:
            print("⚠️ النظام غير مهيأ")
            return

        s = self.ahs.get_status()
        print(f"\n📊 **حالة AHS**")
        print(f"  Status: {s.get('status', '?')}")
        print(f"  Uptime: {s.get('uptime_seconds', 0)}s")
        print(f"  Components: {sum(1 for v in s.get('components', {}).values() if v)}/{len(s.get('components', {}))}")
        print(f"  Tasks: {s.get('stats', {}).get('tasks_processed', 0)}")
        print(f"  Tools: {s.get('tools_count', 0)}")
        print(f"  Skills: {s.get('skills_count', 0)}")
        print(f"  Workers: {s.get('workers_count', 0)}")

    def _cmd_health(self, *args):
        """فحص صحي"""
        if not self.ahs:
            print("⚠️ النظام غير مهيأ")
            return
        h = self.ahs.health_check()
        summary = h.get("summary", {})
        print(f"\n🩺 **Health Check**")
        print(f"  {summary.get('passed', 0)}/{summary.get('total', 0)} checks passed")
        for check in h.get("checks", []):
            icon = "✅" if check.get("status") == "healthy" else "❌"
            print(f"  {icon} {check.get('name', '?')}: {check.get('message', '?')}")

    def _cmd_doctor(self, *args):
        """تشخيص مفصل"""
        if not self.ahs or not self.ahs.doctor:
            print("⚠️ Doctor غير متاح")
            return
        report = self.ahs.doctor.diagnose()
        print(f"\n🔍 **تشخيص النظام**")
        for check in report.get("checks", []):
            icon = "✅" if check.get("status") == "healthy" else "❌"
            print(f"  {icon} {check.get('name', '?')}")
            if check.get("message"):
                print(f"     {check['message']}")

    def _cmd_tools(self, *args):
        """عرض الأدوات"""
        if not self.ahs or not self.ahs.tools:
            print("⚠️ الأدوات غير متاحة")
            return
        tools = self.ahs.tools.list()
        print(f"\n🔧 **الأدوات ({len(tools)})**")
        for t in tools:
            print(f"  • {t['name']}: {t.get('description', '')[:60]}")

    def _cmd_skills(self, *args):
        """عرض المهارات"""
        if not self.ahs or not self.ahs.skills:
            print("⚠️ المهارات غير متاحة")
            return
        skills = self.ahs.skills.list()
        print(f"\n🧠 **المهارات ({len(skills)})**")
        for s in skills:
            print(f"  • {s.get('name', '?')}: {s.get('description', '')[:60]}")

    def _cmd_mode(self, *args):
        """تغيير الوضع"""
        if args:
            self.mode = args[0]
            print(f"✅ تم تغيير الوضع إلى: {self.mode}")
        else:
            print(f"📌 الوضع الحالي: {self.mode}")
            print("   الأوضاع: auto, hybrid, quick, deep, code, flow")

    def _cmd_history(self, *args):
        """سجل الأوامر"""
        print(f"\n📜 **السجل ({len(self.session_log)} أمر)**")
        for i, entry in enumerate(self.session_log[-20:], 1):
            print(f"  {i}. [{entry['mode']}] {entry['task'][:60]}")

    def _cmd_stats(self, *args):
        """إحصائيات"""
        print(f"\n📊 **الإحصائيات**")
        print(f"  الأوامر: {len(self.session_log)}")
        print(f"  وقت التشغيل: {time.time() - self.start_time:.0f}s")
        if self.ahs:
            s = self.ahs.stats
            print(f"  مكالمات Hermes: {s.hermes_calls}")
            print(f"  أدوات: {s.tools_called}")
            print(f"  مهارات: {s.skills_executed}")
            print(f"  أخطاء: {s.errors}")

    def _cmd_clear(self, *args):
        """مسح الشاشة"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print(self.intro)

    def _cmd_save(self, *args):
        """حفظ الجلسة"""
        filename = args[0] if args else f"session_{int(time.time())}.json"
        path = Path("sessions")
        path.mkdir(exist_ok=True)
        filepath = path / filename
        data = {
            "mode": self.mode,
            "commands": self.session_log,
            "saved_at": datetime.now().isoformat(),
        }
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"✅ حفظت الجلسة في {filepath}")

    def _cmd_load(self, *args):
        """تحميل جلسة"""
        if not args:
            print("⚠️ اكتب /load <filename>")
            return
        filepath = Path("sessions") / args[0]
        if not filepath.exists():
            print(f"❌ الملف {filepath} غير موجود")
            return
        data = json.loads(filepath.read_text())
        self.mode = data.get("mode", "auto")
        self.session_log = data.get("commands", [])
        print(f"✅ تم تحميل {len(self.session_log)} أمر")

    def _cmd_export(self, *args):
        filename = args[0] if args else f"log_{int(time.time())}.md"
        lines = ["# AHS Session Log\n"]
        for entry in self.session_log:
            lines.append(f"- **[{entry['mode']}]** {entry['task']}")
            lines.append(f"  → {entry.get('response', '')[:100]}...")
        Path(filename).write_text("\n".join(lines))
        print(f"✅ ملف التصدير: {filename}")

    def _cmd_verbose(self, *args):
        self.verbose = not self.verbose
        print(f"✅ العرض المفصل: {'ON' if self.verbose else 'OFF'}")

    def _cmd_version(self, *args):
        print("🤝 AHS v0.2.0 | Agent Hybrid System")
        print("  Engine: OpenClaw + Hermes (DeepSeek R1)")

    def _cmd_config(self, *args):
        if not self.ahs or not self.ahs.config:
            print("⚠️ الإعدادات غير متاحة")
            return
        summary = self.ahs.config.summary()
        print(f"\n⚙️ **الإعدادات**")
        for k, v in summary.items():
            print(f"  {k}: {v}")

    def _cmd_pipeline(self, *args):
        print(f"\n🔗 **خطوط البيانات**")
        print("  قيد التطوير...")

    def _cmd_events(self, *args):
        print(f"\n📡 **الأحداث**")
        print("  قيد التطوير...")

    def _cmd_plugins(self, *args):
        print(f"\n🧩 **الإضافات**")
        print("  قيد التطوير...")

    def _cmd_scheduler(self, *args):
        print(f"\n⏰ **المهام المجدولة**")
        print("  قيد التطوير...")

    def _process_task(self, task: str):
        """معالجة مهمة"""
        if not self.ahs:
            print("⚠️ النظام غير مهيأ، جاري التهيئة...")
            self.ahs.__class__ = type(self.ahs) if self.ahs else None
            print("❌ لا يمكن معالجة المهمة")
            return

        start = time.time()
        result = self.ahs.process(task, mode=self.mode)
        elapsed = time.time() - start

        # تسجيل
        entry = {
            "task": task[:100],
            "mode": result.get("mode", self.mode),
            "response": result.get("response", "")[:200],
            "elapsed": round(elapsed, 2),
            "time": datetime.now().isoformat(),
        }
        self.session_log.append(entry)

        # عرض
        response = result.get("response", "⚠️ لا رد")
        mode = result.get("mode", self.mode)
        print(f"\n[{mode.upper()}] {response}")
        if self.verbose:
            print(f"\n⏱ {elapsed:.2f}s | التفاصيل: {json.dumps(result, indent=2)[:500]}")

    def emptyline(self):
        pass

    def do_quit(self, arg):
        return True

    def postloop(self):
        print("👋")


def start_repl(ahs=None):
    """تشغيل الـ REPL"""
    repl = AHSREPL(ahs)
    try:
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\n👋")
    except EOFError:
        print("\n👋")


if __name__ == "__main__":
    print("🤝 AHS REPL — واجهة تفاعلية")
    print("⚠️  هذا الإصدار يعمل بدون اتصال Hermes")
    print("   اكتب help للبدء\n")

    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    result = ahs.initialize()
    print(f"✅ {result['initialized']}/{result['total_components']} components initialized\n")

    start_repl(ahs)
