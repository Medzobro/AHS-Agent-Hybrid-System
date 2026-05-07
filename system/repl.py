#!/usr/bin/env python3
"""
AHS - REPL (Read-Eval-Print Loop)
===================================
Interactive command-line interface for AHS.

المميزات:
  - Full interactive session
  - Built-in commands (/help, /status, /health, /tools...)
  - Session export
  - Command history
  - Auto-completion for commands
"""

import json, os, sys, time, cmd, readline, shlex
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class AHSREPL(cmd.Cmd):
    """
    Interactive command-line interface for the system.
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
        """Handle unknown input"""
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
            print(f"❌ Unknown command: /{cmd}")
            print("   Type /help for available commands")

    def _cmd_help(self, *args):
        """Display help"""
        help_text = """
📋 AHS Commands:

  /help              ← عرض هذه المساعدة
  /quit, /exit       ← Exit

  /status            ← System status
  /health            ← Full health check
  /doctor            ← Detailed diagnosis
  /stats             ← Statistics
  /version           ← Version

  /mode [auto|hybrid|quick|deep|code|flow]  ← Change mode
  /verbose           ← Toggle verbose mode

  /tools             ← Show available tools
  /skills            ← Show skills
  /config            ← Show config
  /plugins           ← Show plugins
  /pipeline          ← Show pipelines
  /events            ← Show events
  /scheduler         ← Show scheduled tasks

  /history           ← Command history
  /clear             ← Clear screen
  /save [filename]   ← Save session
  /load [filename]   ← Load session
  /export [filename] ← Export history

Current mode: {mode}

أمثلة:
  🤝 AHS> ما هو AHS؟
  🤝 AHS> اكتب كود Python
  🤝 AHS> /mode deep
  🤝 AHS> /health
""".format(mode=self.mode)
        print(help_text)

    def _cmd_quit(self, *args):
        """Exit system"""
        print("👋 مع السلامة!")
        return True

    def _cmd_status(self, *args):
        """عرض System status"""
        if not self.ahs:
            print("⚠️ System not initialized")
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
            print("⚠️ System not initialized")
            return
        h = self.ahs.health_check()
        summary = h.get("summary", {})
        print(f"\n🩺 **Health Check**")
        print(f"  {summary.get('passed', 0)}/{summary.get('total', 0)} checks passed")
        for check in h.get("checks", []):
            icon = "✅" if check.get("status") == "healthy" else "❌"
            print(f"  {icon} {check.get('name', '?')}: {check.get('message', '?')}")

    def _cmd_doctor(self, *args):
        """Detailed diagnosis"""
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
        """عرض الTools"""
        if not self.ahs or not self.ahs.tools:
            print("⚠️ Tools unavailable")
            return
        tools = self.ahs.tools.list()
        print(f"\n🔧 **الTools ({len(tools)})**")
        for t in tools:
            print(f"  • {t['name']}: {t.get('description', '')[:60]}")

    def _cmd_skills(self, *args):
        """Show skills"""
        if not self.ahs or not self.ahs.skills:
            print("⚠️ Skills unavailable")
            return
        skills = self.ahs.skills.list()
        print(f"\n🧠 **الSkills ({len(skills)})**")
        for s in skills:
            print(f"  • {s.get('name', '?')}: {s.get('description', '')[:60]}")

    def _cmd_mode(self, *args):
        """Change mode"""
        if args:
            self.mode = args[0]
            print(f"✅ تم Change mode إلى: {self.mode}")
        else:
            print(f"📌 Current mode: {self.mode}")
            print("   Modes: auto, hybrid, quick, deep, code, flow")

    def _cmd_history(self, *args):
        """Command history"""
        print(f"\n📜 **السجل ({len(self.session_log)} أمر)**")
        for i, entry in enumerate(self.session_log[-20:], 1):
            print(f"  {i}. [{entry['mode']}] {entry['task'][:60]}")

    def _cmd_stats(self, *args):
        """Statistics"""
        print(f"\n📊 **الStatistics**")
        print(f"  الأوامر: {len(self.session_log)}")
        print(f"  Uptime: {time.time() - self.start_time:.0f}s")
        if self.ahs:
            s = self.ahs.stats
            print(f"  Hermes calls: {s.hermes_calls}")
            print(f"  Tools: {s.tools_called}")
            print(f"  Skills: {s.skills_executed}")
            print(f"  Errors: {s.errors}")

    def _cmd_clear(self, *args):
        """Clear screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print(self.intro)

    def _cmd_save(self, *args):
        """Save session"""
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
        print(f"✅ Session saved to {filepath}")

    def _cmd_load(self, *args):
        """Load session"""
        if not args:
            print("⚠️ Type /load <filename>")
            return
        filepath = Path("sessions") / args[0]
        if not filepath.exists():
            print(f"❌ الملف {filepath} غير موجود")
            return
        data = json.loads(filepath.read_text())
        self.mode = data.get("mode", "auto")
        self.session_log = data.get("commands", [])
        print(f"✅ Loaded {len(self.session_log)} أمر")

    def _cmd_export(self, *args):
        filename = args[0] if args else f"log_{int(time.time())}.md"
        lines = ["# AHS Session Log\n"]
        for entry in self.session_log:
            lines.append(f"- **[{entry['mode']}]** {entry['task']}")
            lines.append(f"  → {entry.get('response', '')[:100]}...")
        Path(filename).write_text("\n".join(lines))
        print(f"✅ Export file: {filename}")

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
        print("  Under development...")

    def _cmd_events(self, *args):
        print(f"\n📡 **الأحداث**")
        print("  Under development...")

    def _cmd_plugins(self, *args):
        print(f"\n🧩 **الإضافات**")
        print("  Under development...")

    def _cmd_scheduler(self, *args):
        print(f"\n⏰ **المهام المجدولة**")
        print("  Under development...")

    def _process_task(self, task: str):
        """معالجة مهمة"""
        if not self.ahs:
            print("⚠️ System not initialized، جاري التهيئة...")
            self.ahs.__class__ = type(self.ahs) if self.ahs else None
            print("❌ Cannot process task")
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
        response = result.get("response", "⚠️ No reply")
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
    print("⚠️  هذا Version يعمل بدون اتصال Hermes")
    print("   اكتب help للبدء\n")

    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    result = ahs.initialize()
    print(f"✅ {result['initialized']}/{result['total_components']} components initialized\n")

    start_repl(ahs)
