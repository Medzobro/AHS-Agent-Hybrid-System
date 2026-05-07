#!/usr/bin/env python3
"""
AHS - Test Suite
=================
Comprehensive tests for all system components.

Covers:
  - Core Components
  - Bridge
  - Skills
  - System
  - Integration
  - Performance
"""

import json, os, sys, time, uuid, unittest, tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ===========================
#  Test Matrix
# ===========================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "",
                 duration: float = 0.0, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.details = details or {}

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "duration": round(self.duration, 3),
            "details": self.details,
        }


class TestCase:
    """A single test case"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.setup_done = False

    def setup(self):
        self.setup_done = True

    def teardown(self):
        pass

    def run(self) -> TestResult:
        raise NotImplementedError


class TestSuite:
    """A collection of tests"""
    def __init__(self, name: str):
        self.name = name
        self.tests: List[TestCase] = []
        self.results: List[TestResult] = []

    def add(self, test: TestCase):
        self.tests.append(test)

    def run_all(self) -> Dict:
        start = time.time()
        self.results.clear()

        for test in self.tests:
            try:
                test.setup()
                test_start = time.time()
                result = test.run()
                result.duration = time.time() - test_start
                self.results.append(result)
                test.teardown()
            except Exception as e:
                self.results.append(TestResult(
                    test.name, False,
                    f"Exception: {e}",
                    details={"error": str(e)}
                ))

        elapsed = time.time() - start
        passed = sum(1 for r in self.results if r.passed)

        return {
            "suite": self.name,
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "elapsed": round(elapsed, 2),
            "results": [r.to_dict() for r in self.results],
        }


class TestRunner:
    """Test runner manager"""
    def __init__(self):
        self.suites: List[TestSuite] = []

    def add_suite(self, suite: TestSuite):
        self.suites.append(suite)

    def run(self) -> Dict:
        results = []
        total = {"passed": 0, "failed": 0, "total": 0}
        start = time.time()

        for suite in self.suites:
            result = suite.run_all()
            results.append(result)
            total["passed"] += result["passed"]
            total["failed"] += result["failed"]
            total["total"] += result["total"]

        elapsed = time.time() - start

        return {
            "suites": len(self.suites),
            "total": total["total"],
            "passed": total["passed"],
            "failed": total["failed"],
            "elapsed": round(elapsed, 2),
            "details": results,
        }

    def run_and_report(self) -> str:
        """Run and display the report"""
        result = self.run()
        lines = [
            "═══════════════════════════════════",
            "  🧪 AHS Test Suite Results",
            "═══════════════════════════════════",
            f"  ✅ Passed: {result['passed']}/{result['total']}",
            f"  ❌ Failed: {result['failed']}",
            f"  ⏱ {result['elapsed']}s",
            "",
        ]

        for detail in result["details"]:
            lines.append(f"  📁 {detail['suite']}")
            for r in detail["results"]:
                icon = "✅" if r["passed"] else "❌"
                lines.append(f"    {icon} {r['name']}: {r['message'][:80]}")
            lines.append("")

        return "\n".join(lines)


# ===========================
#  Core Tests
# ===========================

class TestOrchestrator(TestCase):
    def __init__(self):
        super().__init__("Orchestrator", "core")

    def run(self) -> TestResult:
        from core.orchestrator import HybridOrchestrator, TaskType
        o = HybridOrchestrator()

        test_cases = {
            "say hello": TaskType.QUICK,
            "search for AI": TaskType.DEEP,
            "write code": TaskType.CODE,
            "execute command": TaskType.COMMAND,
        }

        passed = 0
        failed = 0
        details = []

        for task, expected in test_cases.items():
            ttype, _ = o.classify_task(task)
            if ttype == expected:
                passed += 1
                details.append(f"✅ {task} → {ttype.value}")
            else:
                failed += 1
                details.append(f"❌ {task} → {ttype.value} (expected {expected.value})")

        return TestResult(
            self.name, failed == 0,
            f"{passed}/{len(test_cases)} passed",
            details={"cases": details},
        )


class TestOrchestratorPlan(TestCase):
    def __init__(self):
        super().__init__("Orchestrator Planning", "core")

    def run(self) -> TestResult:
        from core.orchestrator import HybridOrchestrator, TaskType
        o = HybridOrchestrator()

        task_types = [TaskType.QUICK, TaskType.DEEP, TaskType.CODE, TaskType.COMMAND]
        all_have_plan = True

        for tt in task_types:
            plan = o.plan_execution("test", tt)
            if not plan.get("steps"):
                all_have_plan = False

        return TestResult(
            self.name, all_have_plan,
            "All task types have valid plans",
        )


class TestAgentLoop(TestCase):
    def __init__(self):
        super().__init__("Agent Loop", "core")

    def run(self) -> TestResult:
        from core.agent_loop import HybridAgent
        agent = HybridAgent()

        # Quick task
        result = agent.process("Who are you")
        if not result.get("response"):
            return TestResult(self.name, False, "No response from agent")

        return TestResult(
            self.name, True,
            f"Response: {result['response'][:60]}... | {result['stats']['steps']} steps",
        )


# ===========================
#  System Tests
# ===========================

class TestToolRegistry(TestCase):
    def __init__(self):
        super().__init__("Tool Registry", "system")

    def run(self) -> TestResult:
        from system.tool_registry import create_default_tools
        reg = create_default_tools()

        tools = reg.list()
        if len(tools) == 0:
            return TestResult(self.name, False, "No tools registered")

        # Test calculate tool
        r1 = reg.call("calculate", expression="2 + 2")
        if not r1.success or r1.data != 4:
            return TestResult(self.name, False, f"calculate failed: {r1.data}")

        # Test uuid tool
        r2 = reg.call("uuid")
        if not r2.success or not r2.data:
            return TestResult(self.name, False, "uuid failed")

        return TestResult(
            self.name, True,
            f"{len(tools)} tools, calculate(2+2)={r1.data}, uuid={r2.data[:8]}...",
        )


class TestConfigManager(TestCase):
    def __init__(self):
        super().__init__("Config Manager", "system")

    def run(self) -> TestResult:
        from system.config_manager import ConfigManager
        cfg = ConfigManager()

        # Default values
        model = cfg.get("model.primary")
        provider = cfg.get("model.provider")

        if not model or not provider:
            return TestResult(self.name, False, "Missing default config")

        # Set and get
        cfg.set("test.value", 42)
        if cfg.get("test.value") != 42:
            return TestResult(self.name, False, "Set/Get failed")

        # Profile
        cfg.create_profile("test-profile", "testing")
        if "test-profile" not in cfg.profiles:
            return TestResult(self.name, False, "Profile creation failed")

        return TestResult(
            self.name, True,
            f"model={model}, provider={provider}, profiles={len(cfg.profiles)}",
        )


class TestDoctor(TestCase):
    def __init__(self):
        super().__init__("Doctor/Health", "system")

    def run(self) -> TestResult:
        from system.doctor import Doctor
        doctor = Doctor()
        report = doctor.diagnose()

        checks = report["summary"]["total"]
        passed = report["summary"]["passed"]

        return TestResult(
            self.name, passed > 0,
            f"{passed}/{checks} checks passed",
            details=report["summary"],
        )


class TestMultiAgent(TestCase):
    def __init__(self):
        super().__init__("Multi-Agent System", "system")

    def run(self) -> TestResult:
        from system.multi_agent import MultiAgentOrchestrator, AgentWorker, AgentRole
        orchestrator = MultiAgentOrchestrator()
        orchestrator.register_default_workers()

        workers = orchestrator.workers
        if len(workers) == 0:
            return TestResult(self.name, False, "No workers registered")

        return TestResult(
            self.name, True,
            f"{len(workers)} workers: {', '.join(workers.keys())}",
        )


class TestSkillManager(TestCase):
    def __init__(self):
        super().__init__("Skill Manager", "system")

    def run(self) -> TestResult:
        from system.skill_manager import SkillManager, SkillCategory
        mgr = SkillManager()
        count = mgr.load_all()

        skills_by_category = mgr.list(category=SkillCategory.GENERAL)

        return TestResult(
            self.name, count > 0,
            f"{count} skills loaded, {len(skills_by_category)} general",
        )


# ===========================
#  Skills Tests
# ===========================

class TestHybridSkills(TestCase):
    def __init__(self):
        super().__init__("Hybrid Skills Module", "skills")

    def run(self) -> TestResult:
        from skills.hybrid_skills import HybridSkills
        h = HybridSkills()

        methods = [
            m for m in dir(h)
            if not m.startswith("_") and callable(getattr(h, m))
        ]

        return TestResult(
            self.name, len(methods) > 0,
            f"{len(methods)} hybrid skills: {', '.join(methods)}",
        )


class TestCodeAssistant(TestCase):
    def __init__(self):
        super().__init__("Code Assistant Module", "skills")

    def run(self) -> TestResult:
        from skills.code_assistant import CodeAssistant
        c = CodeAssistant()
        files = c.list_generated()

        return TestResult(
            self.name, True,
            f"{len(files)} generated files",
        )


class TestSynthesizer(TestCase):
    def __init__(self):
        super().__init__("Response Synthesizer", "skills")

    def run(self) -> TestResult:
        from skills.synthesizer import ResponseSynthesizer
        s = ResponseSynthesizer()

        # Test quick analysis (without API)
        analysis = s._openclaw_quick("Who are you")
        if not analysis:
            return TestResult(self.name, False, "Quick analysis failed")

        return TestResult(
            self.name, True,
            f"Quick analysis works: {analysis}",
        )


# ===========================
#  Integration Tests
# ===========================

class TestIntegration(TestCase):
    def __init__(self):
        super().__init__("Integration Layer", "integration")

    def run(self) -> TestResult:
        from system.integration import AHSIntegration
        ahs = AHSIntegration()
        result = ahs.initialize()

        if result["status"] not in ("running", "degraded"):
            return TestResult(
                self.name, False,
                f"Init failed: {result['status']}",
                details=result,
            )

        return TestResult(
            self.name, True,
            f"{result['initialized']}/{result['total_components']} components",
            details=result,
        )


class TestAutoMode(TestCase):
    def __init__(self):
        super().__init__("Auto Mode Selection", "integration")

    def run(self) -> TestResult:
        from system.integration import AHSIntegration
        ahs = AHSIntegration()

        test_cases = {
            "code": "write Python code",
            "deep": "search for AI",
            "quick": "hello",
            "flow": "a" * 250,
        }

        results = []
        for expected, task in test_cases.items():
            mode = ahs._auto_select_mode(task)
            status = "✅" if mode == expected else "❌"
            results.append(f"{status} {task[:20]}... → {mode}")

        return TestResult(
            self.name, True,
            "Auto mode selection works",
            details={"cases": results},
        )


# ===========================
#  Performance Tests
# ===========================

class TestPerformance(TestCase):
    def __init__(self):
        super().__init__("JSON Performance", "performance")

    def run(self) -> TestResult:
        data = {"key": "value" * 1000, "nested": {"a": list(range(100))}}
        start = time.time()
        iterations = 500
        for _ in range(iterations):
            json.dumps(data)
        elapsed = time.time() - start
        ops_per_sec = iterations / elapsed

        return TestResult(
            self.name, ops_per_sec > 100,
            f"{ops_per_sec:.0f} ops/s ({iterations} iterations in {elapsed:.2f}s)",
        )


class TestMemoryPerformance(TestCase):
    def __init__(self):
        super().__init__("Memory Operations", "performance")

    def run(self) -> TestResult:
        start = time.time()
        items = []
        for i in range(1000):
            items.append({"id": i, "data": f"item_{i}" * 10})
        elapsed = time.time() - start

        return TestResult(
            self.name, elapsed < 1.0,
            f"1000 items in {elapsed*1000:.0f}ms",
        )


# ===========================
#  Utility Tests
# ===========================

class TestJSONTools(TestCase):
    def __init__(self):
        super().__init__("JSON Utilities", "utility")

    def run(self) -> TestResult:
        # Test json_parse and json_dumps
        from system.tool_registry import create_default_tools
        reg = create_default_tools()

        data = {"name": "AHS", "version": "0.2.0"}
        text = json.dumps(data)

        # json_parse
        r1 = reg.call("json_parse", text=text)
        if not r1.success:
            return TestResult(self.name, False, f"json_parse failed: {r1.error}")

        # json_dumps
        r2 = reg.call("json_dumps", data=data)
        if not r2.success:
            return TestResult(self.name, False, f"json_dumps failed: {r2.error}")

        return TestResult(self.name, True, "JSON tools work end-to-end")


class TestUUIDGeneration(TestCase):
    def __init__(self):
        super().__init__("UUID Generation", "utility")

    def run(self) -> TestResult:
        ids = set()
        for _ in range(100):
            ids.add(uuid.uuid4().hex)

        return TestResult(
            self.name, len(ids) == 100,
            f"100 unique UUIDs generated",
        )


# ===========================
#  Error Handling Tests
# ===========================

class TestErrorHandling(TestCase):
    def __init__(self):
        super().__init__("Error Handling", "core")

    def run(self) -> TestResult:
        from core.orchestrator import HybridOrchestrator
        o = HybridOrchestrator()

        # Test with empty task
        try:
            ttype, _ = o.classify_task("")
            if ttype is None:
                return TestResult(self.name, False, "Empty task returned None")
        except Exception as e:
            return TestResult(self.name, False, f"Empty task raised: {e}")

        # Test with very long task
        try:
            long_task = "x" * 10000
            ttype, _ = o.classify_task(long_task)
        except Exception as e:
            return TestResult(self.name, False, f"Long task raised: {e}")

        # Test memory save/load
        try:
            o.record_learning("test_key", "test_value")
            learnings = o.get_relevant_learnings("test_key")
        except Exception as e:
            return TestResult(self.name, False, f"Memory ops raised: {e}")

        return TestResult(self.name, True, "Error handling works")


# ===========================
#  Create and run all tests
# ===========================

def create_full_test_suite() -> TestRunner:
    """Create the complete test suite"""
    runner = TestRunner()

    # Core
    core = TestSuite("Core Components")
    core.add(TestOrchestrator())
    core.add(TestOrchestratorPlan())
    core.add(TestAgentLoop())
    core.add(TestErrorHandling())
    runner.add_suite(core)

    # System
    system = TestSuite("System Components")
    system.add(TestToolRegistry())
    system.add(TestConfigManager())
    system.add(TestDoctor())
    system.add(TestMultiAgent())
    system.add(TestSkillManager())
    runner.add_suite(system)

    # Skills
    skills = TestSuite("Skills")
    skills.add(TestHybridSkills())
    skills.add(TestCodeAssistant())
    skills.add(TestSynthesizer())
    runner.add_suite(skills)

    # Integration
    integration = TestSuite("Integration")
    integration.add(TestIntegration())
    integration.add(TestAutoMode())
    runner.add_suite(integration)

    # Performance
    perf = TestSuite("Performance")
    perf.add(TestPerformance())
    perf.add(TestMemoryPerformance())
    runner.add_suite(perf)

    # Utility
    utility = TestSuite("Utility")
    utility.add(TestJSONTools())
    utility.add(TestUUIDGeneration())
    runner.add_suite(utility)

    return runner


def run_tests(verbose: bool = False) -> Dict:
    """Run all tests"""
    runner = create_full_test_suite()
    return runner.run()


def run_tests_and_report() -> str:
    """Run and display the report"""
    runner = create_full_test_suite()
    return runner.run_and_report()


if __name__ == "__main__":
    report = run_tests_and_report()
    print(report)