#!/usr/bin/env python3
"""
AHS - Hybrid Demo
==================
Interactive demo showing how OpenClaw + Hermes work together.
Runs 3 different scenarios and shows the flow step by step.
"""

import os
import sys
import time

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
    print(f" {BOLD}📋 Scenario: {name}{RESET}")
    print(f" {'='*50}")
    print(f" 📥 Task: \"{task}\"\n")

    if flow_type == "code":
        # Code Assistant Demo
        print_step("🤖", "OpenClaw", "Analyzing request...")
        time.sleep(0.5)
        print_step("🤖", "OpenClaw", "Classifying: programming/code request")
        print_step("🤖", "OpenClaw", "Planning: Hermes writes code ← I save it")
        time.sleep(0.5)
        print_step("🧠", "Hermes", "Writing code... (DeepSeek R1)")
        
        c = CodeAssistant()
        start = time.time()
        r = c.write_code(task, language="python")
        elapsed = time.time() - start
        
        if r["success"]:
            print_step("🤖", "OpenClaw", f"Received code ({r['lines']} lines)")
            print_step("🤖", "OpenClaw", f"Saving to {r['filename']}")
            print_step("✅", "AHS", f"Done! ⏱ {r['elapsed']}s")
            print(f"\n  📄 {GREEN}Code snippet:{RESET}")
            for line in r["code"].strip().split("\n")[:5]:
                print(f"    {line}")
        else:
            print_step("❌", "AHS", f"Error: {r.get('error')}")

    elif flow_type == "flow":
        # Hybrid Flow Demo
        print_step("🤖", "OpenClaw", "Analyzing task and planning flow...")
        time.sleep(0.5)
        
        f = HybridFlow()
        start = time.time()
        r = f.run(task)
        elapsed = time.time() - start
        
        print(f"\n  {BOLD}📊 Flow log:{RESET}")
        for s in r["log"]:
            emoji = "🤖" if s["actor"] == "openclaw" else "🧠"
            print(f"    {emoji} {s['actor']} → {s['action']}")
        
        print(f"\n  📤 {GREEN}{r['final'][:300]}{RESET}")
        print(f"\n  ⏱ {r['elapsed']}s | {r['steps']} steps | Type: {r['flow_type']}")

    elif flow_type == "hybrid":
        # Response Synthesizer Demo
        print_step("🤖", "OpenClaw", "Understanding context immediately...")
        time.sleep(0.3)
        print_step("🧠", "Hermes", "Thinking deeply... (DeepSeek R1)")
        
        s = ResponseSynthesizer()
        start = time.time()
        r = s.synthesize(task)
        elapsed = time.time() - start
        
        print(f"\n  {BOLD}🔬 Analysis:{RESET}")
        print(f"    🤖 OpenClaw classified: {r['openclaw']}")
        print(f"    🧠 Hermes thought: {r['hermes'][:100]}...")
        print(f"\n  📤 {GREEN}{r['final'][:300]}{RESET}")
        print(f"\n  ⏱ {r['elapsed']}s | Hybrid mode")


def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f" {BOLD}{CYAN}🎬 AHS Hybrid Agent — Interactive Demos{RESET}")
    print(f" {BOLD}   OpenClaw + Hermes Collaborating{RESET}")
    print(f"{BOLD}{'='*50}{RESET}")

    # Scenario 1: Code
    demo_scenario(
        "Writing Python Code",
        "Function that returns sum of two numbers",
        "code"
    )

    # Scenario 2: Hybrid Flow
    demo_scenario(
        "Full Hybrid Flow",
        "Give me a simple AI Agent example",
        "flow"
    )

    # Scenario 3: Hybrid Synthesizer
    demo_scenario(
        "Hybrid Mode",
        "Summarize the AI Agent in one sentence",
        "hybrid"
    )

    print(f"\n{BOLD}{GREEN}{'='*50}{RESET}")
    print(f" {BOLD}{GREEN}✅ 3 Complete Scenarios!{RESET}")
    print(f" {BOLD}🔗 https://github.com/Medzobro/AHS-Agent-Hybrid-System{RESET}")
    print(f"{BOLD}{GREEN}{'='*50}{RESET}\n")


if __name__ == "__main__":
    main()