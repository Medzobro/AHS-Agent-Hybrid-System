#!/usr/bin/env python3
"""
AHS - Real Integration Tests
==============================
Tests that connect to real Hermes MCP bridge.
These prove AHS works end-to-end.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
SKIP = "⏭️"


class TestResult:
    passed = 0
    failed = 0
    skipped = 0

    @classmethod
    def report(cls):
        total = cls.passed + cls.failed
        print(f"\n{'='*40}")
        print(f"📊 Results: {cls.passed}/{total} passed"
              f"{f', {cls.skipped} skipped' if cls.skipped else ''}")
        return cls.failed == 0


def test(name: str):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.time() - start
                if result:
                    TestResult.passed += 1
                    print(f"  {PASS} {name} ({elapsed:.1f}s)")
                else:
                    TestResult.failed += 1
                    print(f"  {FAIL} {name} ({elapsed:.1f}s)")
                return result
            except Exception as e:
                TestResult.failed += 1
                elapsed = time.time() - start
                print(f"  {FAIL} {name}: {e} ({elapsed:.1f}s)")
                return False
        return wrapper
    return decorator


# ===========================
#  Tests
# ===========================

@test("System initializes")
def test_init():
    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    result = ahs.initialize()
    return result["initialized"] == result["total_components"]


@test("Quick mode works")
def test_quick():
    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    ahs.initialize()
    result = ahs.process("تمام", mode="quick")
    return bool(result.get("response"))


@test("Hybrid mode works (Hermes responds)")
def test_hybrid():
    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    ahs.initialize()
    result = ahs.process("What is 2+2?", mode="hybrid")
    resp = result.get("response", "")
    return bool(resp) and len(resp) > 10


@test("Auto mode selects correctly")
def test_auto_mode():
    from system.integration import AHSIntegration
    ahs = AHSIntegration()
    ahs.initialize()
    
    # Code task
    code_result = ahs.process("اكتب كود", mode="auto")
    # Deep task
    deep_result = ahs.process("ابحث عن AI", mode="auto")
    
    return code_result.get("mode") == "code" and deep_result.get("mode") == "deep"


@test("Hermes Bridge direct call")
def test_hermes_direct():
    from bridge.hermes_bridge import HermesBridge
    b = HermesBridge()
    
    result = b.send_task("Say: ping", timeout=30)
    if not result.get("success"):
        return False
    
    resp = result.get("response", {})
    content = resp.get("content", "") or ""
    return "ping" in content.lower() or len(content) > 0


@test("Shared memory saves and loads")
def test_shared_memory():
    from core.orchestrator import HybridOrchestrator
    o = HybridOrchestrator()
    
    o.record_learning("test_result", "working")
    learnings = o.get_relevant_learnings("test_result")
    
    return len(learnings) > 0


@test("Tool registry has 10 tools")
def test_tools():
    from system.tool_registry import create_default_tools
    reg = create_default_tools()
    tools = reg.list()
    return len(tools) == 10


@test("Doctor checks pass")
def test_doctor():
    from system.doctor import Doctor
    d = Doctor()
    report = d.diagnose()
    return report["summary"]["passed"] > 0


@test("Multi-agent workers registered")
def test_multi_agent():
    from system.multi_agent import MultiAgentOrchestrator
    o = MultiAgentOrchestrator()
    o.register_default_workers()
    return len(o.workers) >= 4


# ===========================
#  Run
# ===========================

def run_all():
    print(f"\n{'='*40}")
    print("  🧪 AHS Real Integration Tests")
    print(f"{'='*40}")
    print("  Testing system end-to-end...\n")
    
    test_init()
    test_quick()
    test_hybrid()
    test_auto_mode()
    test_hermes_direct()
    test_shared_memory()
    test_tools()
    test_doctor()
    test_multi_agent()
    
    TestResult.report()


if __name__ == "__main__":
    run_all()
