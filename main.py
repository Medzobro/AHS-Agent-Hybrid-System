#!/usr/bin/env python3
"""
AHS - Agent Hybrid System
==========================
النظام الرئيسي — نقطة الدخول الموحدة

الاستخدام:
  python3 main.py "مهمتك هنا"
  python3 main.py --hybrid "سؤال يحتاج تفكير"
  python3 main.py --code "وصف الكود"
  python3 main.py --interactive
  python3 main.py --demo
  python3 main.py --status
"""

import json, os, sys, time, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent_loop import HybridAgent
from core.orchestrator_v2 import HybridFlow
from skills.hybrid_skills import HybridSkills
from skills.synthesizer import ResponseSynthesizer
from skills.code_assistant import CodeAssistant
from demo import demo_scenario

GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


class AHS:
    """Agent Hybrid System — الواجهة الرئيسية."""

    def __init__(self):
        self.agent = HybridAgent()
        self.skills = HybridSkills()
        self.synth = ResponseSynthesizer()
        self.code = CodeAssistant()
        self.flow = HybridFlow()
        self.start_time = time.time()

    def process(self, task: str, show_thinking: bool = False,
                hybrid: bool = False, code_mode: bool = False,
                flow_mode: bool = False) -> dict:
        
        if code_mode:
            r = self.code.write_code(task)
            if r["success"]:
                resp = {
                    "task": task,
                    "response": (
                        f"✅ **الكود جاهز!**\n📄 `{r['filename']}` ({r['lines']} سطر)\n"
                        f"💾 محفوظ في: `generated/`\n⏱ {r['elapsed']}s"
                    ),
                    "stats": {"elapsed_seconds": r["elapsed"]},
                }
                if show_thinking:
                    print(f"📄 أول 200 حرف:\n{r['code'][:200]}")
                return resp
            return {"task": task, "response": f"❌ {r.get('error')}", "stats": {}}

        if flow_mode:
            r = self.flow.run(task)
            return {
                "task": task, "flow_type": r["flow_type"],
                "response": r["final"],
                "stats": {"elapsed_seconds": r["elapsed"], "steps": r["steps"]},
                "log": r["log"],
            }

        if hybrid:
            r = self.synth.synthesize(task)
            return {
                "task": task, "classification": "hybrid",
                "response": r["final"],
                "stats": {"elapsed_seconds": r["elapsed"], "hybrid": True},
            }

        result = self.agent.process(task)
        if show_thinking and "execution" in result:
            for step in result.get("execution", []):
                if step.get("result"):
                    print(f"  🔧 {step['step']} ← {step['by']}")
        return result

    def interactive(self, mode: str = "normal"):
        modes = {
            "normal": "🔧 Standard",
            "hybrid": "🤝 Hybrid (OpenClaw + Hermes)",
            "code": "💻 Code Assistant",
        }
        print(f"\n{BOLD}{'='*50}{RESET}")
        print(f" {BOLD}🤖 AHS v{self.agent.version} — {modes.get(mode, mode)}{RESET}")
        print(f" {BOLD}🧠 DeepSeek R1 + OpenClaw{RESET}")
        print(f"{BOLD}{'='*50}{RESET}")
        print(" أكتب مهمتك (خروج للخروج):\n")

        kwargs_map = {
            "normal": {},
            "hybrid": {"hybrid": True},
            "code": {"code_mode": True},
        }
        kwargs = kwargs_map.get(mode, {})

        while True:
            try:
                task = input(self._prompt_arrow()).strip()
                if not task: continue
                if task.lower() in ["exit", "quit", "خروج"]: break
                if task.lower() in ["status", "حالة"]: self.status(); continue
                if task.lower() in ["help", "مساعدة"]: self._show_help(); continue

                start = time.time()
                result = self.process(task, **kwargs)
                elapsed = time.time() - start

                print(f"\n📤 {result['response']}")
                print(f"⚡ {elapsed:.1f}s\n")
            except KeyboardInterrupt:
                print("\n👋"); break
            except Exception as e:
                print(f"❌ {e}")

    def run_demo(self):
        print(f"\n{BOLD}{'='*50}{RESET}")
        print(f" {BOLD}{CYAN}🎬 AHS — العروض التفاعلية{RESET}")
        print(f" {BOLD}   OpenClaw + Hermes معاً{RESET}")
        print(f"{BOLD}{'='*50}{RESET}")

        demo_scenario("كتابة كود Python", "دالة ترجع مجموع رقمين", "code")
        demo_scenario("التدفق الهجين الكامل", "ما هو الـ AI Agent", "flow")
        demo_scenario("الوضع الهجين", "لخص الـ AI Agent في جملة", "hybrid")

        print(f"\n{BOLD}{GREEN}{'='*50}{RESET}")
        print(f" {BOLD}✅ 3 سيناريوهات!{RESET}")
        print(f"{BOLD}{GREEN}{'='*50}{RESET}\n")

    def status(self):
        st = self.agent.status()
        st["uptime_seconds"] = round(time.time() - self.start_time)
        st["generated_files"] = len(self.code.list_generated())
        print(json.dumps(st, indent=2, ensure_ascii=False))

    def _prompt_arrow(self): return f"{GREEN}❯{RESET} "
    
    def _show_help(self):
        print(""" الأوامر:
  help / مساعدة   ← هذه القائمة
  status / حالة   ← حالة النظام
  exit / خروج    ← إنهاء
""")


def main():
    parser = argparse.ArgumentParser(
        description="AHS - Agent Hybrid System (OpenClaw + Hermes)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 أمثلة:
  python3 main.py "مهمتي هنا"          # وضع عادي
  python3 main.py --hybrid "سؤال"      # وضع هجين
  python3 main.py --code "وصف كود"     # كتابة كود
  python3 main.py --flow "وصف"         # تدفق متعدد الخطوات
  python3 main.py -i                   # تفاعلي
  python3 main.py --demo               # عروض تفاعلية
  python3 main.py -s                   # حالة النظام
"""
    )
    parser.add_argument("task", nargs="?", help="المهمة")
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--code", action="store_true")
    parser.add_argument("--flow", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("-s", "--status", action="store_true")
    parser.add_argument("-t", "--thinking", action="store_true")
    parser.add_argument("--skill", choices=["research", "review", "plan", "learn"])

    args = parser.parse_args()
    ahs = AHS()

    if args.status:
        ahs.status()
    elif args.demo:
        ahs.run_demo()
    elif args.skill and args.task:
        maps = {
            "research": ahs.skills.research_and_summarize,
            "review": ahs.skills.code_review,
            "plan": ahs.skills.plan_project,
            "learn": ahs.skills.learn_new_skill,
        }
        r = maps[args.skill](args.task)
        resp = r.get("response", {})
        print(f"\n📤 {resp.get('content', '')[:600]}")
    elif args.interactive:
        if args.hybrid: mode = "hybrid"
        elif args.code: mode = "code"
        else: mode = "normal"
        ahs.interactive(mode=mode)
    elif args.task:
        result = ahs.process(
            args.task,
            show_thinking=args.thinking,
            hybrid=args.hybrid,
            code_mode=args.code,
            flow_mode=args.flow,
        )
        print(f"\n📤 {result['response']}")
        print(f"⚡ {result['stats'].get('elapsed_seconds', 0):.1f}s")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


# ============================================================
#  __summary__
# ============================================================
# Main entry point for AHS Agent Hybrid System
# 
# Commands:
#   --info       System information and component status
#   --hybrid     Hybrid mode (OpenClaw + Hermes)
#   --code       Code generation mode
#   --flow       Multi-step flow mode
#   --demo       Run demo scenarios
#   --skill      Test hybrid skills
#   -i           Interactive REPL mode
# 
# Architecture:
#   core/orchestrator.py      Task classification & planning
#   core/orchestrator_v2.py   Multi-step flow orchestration
#   core/agent_loop.py        Complete agent execution loop
#   bridge/hermes_bridge.py   Hermes AI communication bridge
#   skills/*.py               Hybrid skills and code assistant
#   system/*.py               Supporting systems (15 modules)
# 
# Exit codes:
#   0  Success
#   1  General error
#   2  Configuration error
#   3  Hermes bridge error
