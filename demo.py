#!/usr/bin/env python3
"""
AHS - Hybrid Demo
==================
عرض تفاعلي يوضح كيف OpenClaw + Hermes يشتغلون معاً.
يشغل 3 سيناريوهات مختلفة ويعرض التدفق خطوة بخطوة.
"""

import json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from core.orchestrator_v2 import HybridFlow
from skills.code_assistant import CodeAssistant
from skills.synthesizer import ResponseSynthesizer

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_step(emoji: str, actor: str, msg: str):
    color = CYAN if actor == "OpenClaw" else YELLOW
    print(f"  {emoji} {color}{BOLD}{actor}{RESET} → {msg}")


def demo_scenario(name: str, task: str, flow_type: str):
    print(f"\n{'='*50}")
    print(f" {BOLD}📋 السيناريو: {name}{RESET}")
    print(f" {'='*50}")
    print(f" 📥 المهمة: \"{task}\"\n")

    if flow_type == "code":
        # Code Assistant Demo
        print_step("🤖", "OpenClaw", "أحلل الطلب...")
        time.sleep(0.5)
        print_step("🤖", "OpenClaw", "أصنفه: طلب برمجة/كود")
        print_step("🤖", "OpenClaw", "أخطط: Hermes يكتب الكود ← أنا أحفظه")
        time.sleep(0.5)
        print_step("🧠", "Hermes", "يكتب الكود... (DeepSeek R1)")
        
        c = CodeAssistant()
        start = time.time()
        r = c.write_code(task, language="python")
        elapsed = time.time() - start
        
        if r["success"]:
            print_step("🤖", "OpenClaw", f"أستلم الكود ({r['lines']} سطر)")
            print_step("🤖", "OpenClaw", f"أحفظه في {r['filename']}")
            print_step("✅", "AHS", f"تم! ⏱ {r['elapsed']}s")
            print(f"\n  📄 {GREEN}مقتطف من الكود:{RESET}")
            for line in r["code"].strip().split("\n")[:5]:
                print(f"    {line}")
        else:
            print_step("❌", "AHS", f"خطأ: {r.get('error')}")

    elif flow_type == "flow":
        # Hybrid Flow Demo
        print_step("🤖", "OpenClaw", "أحلل المهمة وأخطط للتدفق...")
        time.sleep(0.5)
        
        f = HybridFlow()
        start = time.time()
        r = f.run(task)
        elapsed = time.time() - start
        
        print(f"\n  {BOLD}📊 سجل التدفق:{RESET}")
        for s in r["log"]:
            emoji = "🤖" if s["actor"] == "openclaw" else "🧠"
            print(f"    {emoji} {s['actor']} → {s['action']}")
        
        print(f"\n  📤 {GREEN}{r['final'][:300]}{RESET}")
        print(f"\n  ⏱ {r['elapsed']}s | {r['steps']} خطوات | نوع: {r['flow_type']}")

    elif flow_type == "hybrid":
        # Response Synthesizer Demo
        print_step("🤖", "OpenClaw", "أفهم السياق فوراً...")
        time.sleep(0.3)
        print_step("🧠", "Hermes", "أفكر عميقاً... (DeepSeek R1)")
        
        s = ResponseSynthesizer()
        start = time.time()
        r = s.synthesize(task)
        elapsed = time.time() - start
        
        print(f"\n  {BOLD}🔬 التحليل:{RESET}")
        print(f"    🤖 OpenClaw صنّف: {r['openclaw']}")
        print(f"    🧠 Hermes فكر: {r['hermes'][:100]}...")
        print(f"\n  📤 {GREEN}{r['final'][:300]}{RESET}")
        print(f"\n  ⏱ {r['elapsed']}s | وضع Hybrid")


def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f" {BOLD}{CYAN}🎬 AHS Hybrid Agent — العروض التفاعلية{RESET}")
    print(f" {BOLD}   OpenClaw + Hermes يتعاونون{RESET}")
    print(f"{BOLD}{'='*50}{RESET}")

    # سيناريو 1: كود
    demo_scenario(
        "كتابة كود Python",
        "دالة ترجع مجموع رقمين",
        "code"
    )

    # سيناريو 2: تدفق هجين
    demo_scenario(
        "التدفق الهجين الكامل",
        "عطني مثال AI Agent بسيط",
        "flow"
    )

    # سيناريو 3: Hybrid Synthesizer
    demo_scenario(
        "الوضع الهجين (Hybrid Mode)",
        "لخص الـ AI Agent في جملة",
        "hybrid"
    )

    print(f"\n{BOLD}{GREEN}{'='*50}{RESET}")
    print(f" {BOLD}{GREEN}✅ 3 سيناريوهات كاملة!{RESET}")
    print(f" {BOLD}🔗 https://github.com/Medzobro/AHS-Agent-Hybrid-System{RESET}")
    print(f"{BOLD}{GREEN}{'='*50}{RESET}\n")


if __name__ == "__main__":
    main()
