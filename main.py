#!/usr/bin/env python3
"""
AHS - Agent Hybrid System
==========================
النظام الرئيسي — نقطة الدخول الموحدة

الاستخدام:
  python3 main.py "مهمتك هنا"
  python3 main.py --hybrid "سؤال يحتاج تفكير"
  python3 main.py --interactive
  python3 main.py --status
"""

import json
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent_loop import HybridAgent
from skills.hybrid_skills import HybridSkills
from skills.synthesizer import ResponseSynthesizer


class AHS:
    """Agent Hybrid System — الواجهة الرئيسية."""

    def __init__(self):
        self.agent = HybridAgent()
        self.skills = HybridSkills()
        self.synth = ResponseSynthesizer()
        self.start_time = time.time()

    def process(self, task: str, show_thinking: bool = False,
                hybrid: bool = False) -> dict:
        if hybrid:
            result = self.synth.synthesize(task)
            resp = {
                "task": task,
                "classification": "hybrid",
                "response": result["final"],
                "stats": {"elapsed_seconds": result["elapsed"], "hybrid": True},
            }
            if show_thinking and result.get("hermes"):
                print(f"🤔 Hermes: {result['hermes'][:200]}")
            return resp

        result = self.agent.process(task)

        if show_thinking and "execution" in result:
            for step in result.get("execution", []):
                if step.get("result"):
                    print(f"🔧 {step['step']} ← {step['by']}: {step['result'][:120]}")

        return result

    def interactive(self, hybrid: bool = False):
        mode = "🤝 Hybrid" if hybrid else "🔧 Standard"
        print(f"\n{'='*50}")
        print(f"🤖 AHS v{self.agent.version} — {mode} Mode")
        print(f"🧠 DeepSeek R1 + OpenClaw")
        print(f"{'='*50}")
        print("أكتب مهمتك (خروج للخروج):\n")

        while True:
            try:
                task = input("❯ ").strip()
                if not task:
                    continue
                if task.lower() in ["exit", "quit", "خروج"]:
                    print("مع السلامة 👋")
                    break
                if task.lower() in ["status", "حالة"]:
                    self.status()
                    continue

                start = time.time()
                result = self.process(task, hybrid=hybrid)
                elapsed = time.time() - start

                print(f"\n📤 {result['response']}")
                print(f"⚡ {elapsed:.1f}s\n")

            except KeyboardInterrupt:
                print("\n👋")
                break
            except Exception as e:
                print(f"❌ {e}")

    def status(self):
        st = self.agent.status()
        st["uptime_seconds"] = round(time.time() - self.start_time)
        st["hybrid_skills"] = len([
            m for m in dir(self.skills)
            if not m.startswith("_") and callable(getattr(self.skills, m))
        ])
        print(json.dumps(st, indent=2, ensure_ascii=False))

    def run_skill(self, skill: str, task: str):
        skills_map = {
            "research": self.skills.research_and_summarize,
            "review": self.skills.code_review,
            "plan": self.skills.plan_project,
            "learn": self.skills.learn_new_skill,
        }
        fn = skills_map.get(skill)
        if not fn:
            print(f"❌ مهارة غير موجودة. المتاحة: {', '.join(skills_map.keys())}")
            return
        r = fn(task)
        resp = r.get("response", {})
        content = resp.get("content", "")
        print(f"\n📤 {content[:600]}")


def main():
    parser = argparse.ArgumentParser(
        description="AHS - Agent Hybrid System (OpenClaw + Hermes)"
    )
    parser.add_argument("task", nargs="?", help="المهمة")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="وضع المحادثة")
    parser.add_argument("--hybrid", action="store_true",
                        help="وضع Hybrid (OpenClaw + Hermes معاً)")
    parser.add_argument("-s", "--status", action="store_true",
                        help="حالة النظام")
    parser.add_argument("-t", "--thinking", action="store_true",
                        help="إظهار التفكير")
    parser.add_argument("--skill", choices=["research", "review", "plan", "learn"],
                        help="تشغيل مهارة محددة")

    args = parser.parse_args()
    ahs = AHS()

    if args.status:
        ahs.status()
    elif args.skill and args.task:
        ahs.run_skill(args.skill, args.task)
    elif args.interactive:
        ahs.interactive(hybrid=args.hybrid)
    elif args.task:
        result = ahs.process(args.task, show_thinking=args.thinking,
                             hybrid=args.hybrid)
        print(f"\n📤 {result['response']}")
        print(f"⚡ {result['stats']['elapsed_seconds']:.1f}s")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
