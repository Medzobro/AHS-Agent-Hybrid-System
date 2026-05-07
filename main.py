#!/usr/bin/env python3
"""
AHS - Agent Hybrid System
==========================
النظام الرئيسي — نقطة الدخول الموحدة

الاستخدام:
  python3 main.py "مهمتك هنا"
  python3 main.py --interactive
  python3 main.py --status
"""

import json
import os
import sys
import time
import argparse
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent_loop import HybridAgent
from core.orchestrator import TaskType
from skills.hybrid_skills import HybridSkills


class AHS:
    """
    Agent Hybrid System — الواجهة الرئيسية.
    """

    def __init__(self):
        self.agent = HybridAgent()
        self.skills = HybridSkills()
        self.start_time = time.time()

    def process(self, task: str, show_thinking: bool = False) -> Dict:
        """معالجة مهمة وعرض النتيجة"""
        result = self.agent.process(task)

        if show_thinking:
            for step in result["execution"]:
                if step.get("result"):
                    print(f"\n🔧 {step['step']} ← {step['by']}")
                    print(f"   {step['result'][:200]}")

        return result

    def interactive(self):
        """وضع المحادثة التفاعلية"""
        print(f"\n{'='*50}")
        print(f"🤖 **{self.agent.name}** v{self.agent.version}")
        print(f"🧠 النموذج: DeepSeek R1 (وضع التفكير)")
        print(f"🤝 شركاء: OpenClaw + Hermes")
        print(f"{'='*50}")
        print("أكتب مهمتك (أو exit للخروج):\n")

        while True:
            try:
                task = input("❯ ").strip()
                if not task:
                    continue
                if task.lower() in ["exit", "quit", "خروج"]:
                    print("مع السلامة 👋")
                    break
                if task.lower() in ["status", "حالة"]:
                    print(json.dumps(self.agent.status(), indent=2, ensure_ascii=False))
                    continue

                start = time.time()
                result = self.process(task)
                elapsed = time.time() - start

                print(f"\n📤 {result['response']}")
                print(f"⚡ {elapsed:.1f}s | {result['stats']['steps']} steps")

            except KeyboardInterrupt:
                print("\n👋")
                break
            except Exception as e:
                print(f"❌ {e}")

    def status(self):
        """عرض حالة النظام"""
        status = self.agent.status()
        uptime = time.time() - self.start_time
        status["uptime_seconds"] = round(uptime)
        status["hybrid_skills_count"] = len([
            m for m in dir(self.skills)
            if not m.startswith("_") and callable(getattr(self.skills, m))
        ])
        print(json.dumps(status, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="AHS - Agent Hybrid System (OpenClaw + Hermes)"
    )
    parser.add_argument("task", nargs="?", help="المهمة")
    parser.add_argument("-i", "--interactive", action="store_true", help="وضع المحادثة")
    parser.add_argument("-s", "--status", action="store_true", help="حالة النظام")
    parser.add_argument("-t", "--thinking", action="store_true", help="إظهار التفكير")

    args = parser.parse_args()

    ahs = AHS()

    if args.status:
        ahs.status()
    elif args.interactive:
        ahs.interactive()
    elif args.task:
        result = ahs.process(args.task, show_thinking=args.thinking)
        print(f"\n📤 {result['response']}")
        print(f"⚡ {result['stats']['elapsed_seconds']:.1f}s")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
