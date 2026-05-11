"""AHS v1.0 — Unit Tests for ToolRegistry + AHSIntegration"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from system.tool_registry import ToolRegistry, ToolSpec, ToolResult, ToolCategory, create_default_tools
from system.integration import AHSIntegration, bootstrap


# ─── ToolRegistry Tests ───────────────────────────────────────

class TestToolSpec:
    def test_create_tool(self):
        fn = lambda ctx: "hello"
        tool = ToolSpec(name="greet", description="Says hello", handler=fn, category=ToolCategory.UTILITY)
        assert tool.name == "greet"
        assert tool.category == ToolCategory.UTILITY
        assert tool.handler is fn

    def test_to_dict(self):
        fn = lambda ctx: 42
        tool = ToolSpec(name="answer", description="The answer", handler=fn, category=ToolCategory.UTILITY)
        d = tool.to_dict()
        assert d["name"] == "answer"
        assert d["category"] == "utility"

    def test_result_ok(self):
        r = ToolResult.ok("done")
        assert r.success is True
        assert r.data == "done"

    def test_result_fail(self):
        r = ToolResult.fail("error msg")
        assert r.success is False
        assert r.error == "error msg"

    def test_result_to_dict_ok(self):
        r = ToolResult.ok({"a": 1})
        d = r.to_dict()
        assert d["success"] is True
        assert isinstance(d["data"], str)
        assert """{"a": 1}""" in d["data"] or "'a': 1" in d["data"]

    def test_result_to_dict_fail(self):
        r = ToolResult.fail("fail")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "fail"


class TestToolRegistry:
    @pytest.fixture
    def reg(self):
        return ToolRegistry()

    def test_register_and_get(self, reg):
        tool = ToolSpec(name="ping", description="Ping test", handler=lambda ctx: "pong", category=ToolCategory.UTILITY)
        reg.register(tool)
        assert reg.get("ping") is tool

    def test_register_many(self, reg):
        tools = [
            ToolSpec(name="a", description="A", handler=lambda ctx: 1, category=ToolCategory.UTILITY),
            ToolSpec(name="b", description="B", handler=lambda ctx: 2, category=ToolCategory.UTILITY),
        ]
        reg.register_many(tools)
        assert reg.get("a") is tools[0]
        assert reg.get("b") is tools[1]

    def test_unregister(self, reg):
        tool = ToolSpec(name="tmp", description="T", handler=lambda ctx: 0, category=ToolCategory.UTILITY)
        reg.register(tool)
        reg.unregister("tmp")
        assert reg.get("tmp") is None

    def test_list_all(self, reg):
        reg.register(ToolSpec(name="t1", description="1", handler=lambda ctx: 1, category=ToolCategory.UTILITY))
        reg.register(ToolSpec(name="t2", description="2", handler=lambda ctx: 2, category=ToolCategory.CODE))
        all_tools = reg.list()
        assert len(all_tools) == 2

    def test_list_by_category(self, reg):
        reg.register(ToolSpec(name="t1", description="1", handler=lambda ctx: 1, category=ToolCategory.UTILITY))
        reg.register(ToolSpec(name="t2", description="2", handler=lambda ctx: 2, category=ToolCategory.CODE))
        utils = reg.list(category=ToolCategory.UTILITY)
        assert len(utils) == 1
        assert utils[0].name == "t1"

    def test_search(self, reg):
        reg.register(ToolSpec(name="web-search", description="Search web", handler=lambda ctx: None, category=ToolCategory.UTILITY))
        reg.register(ToolSpec(name="file-read", description="Read a file", handler=lambda ctx: None, category=ToolCategory.UTILITY))
        results = reg.search("web")
        assert len(results) >= 1
        assert results[0].name == "web-search"

    def test_call_success(self, reg):
        tool = ToolSpec(name="add", description="Add nums", handler=lambda **kw: kw["a"] + kw["b"], category=ToolCategory.UTILITY)
        reg.register(tool)
        result = reg.call("add", a=1, b=2)
        assert result.success is True
        assert result.data == 3

    def test_call_with_ctx(self, reg):
        tool = ToolSpec(name="ping", description="ping", handler=lambda **kw: "pong", category=ToolCategory.UTILITY)
        reg.register(tool)
        result = reg.call("ping")
        assert result.success is True
        assert result.data == "pong"

    def test_call_error(self, reg):
        tool = ToolSpec(name="crash", description="Raise error", handler=lambda ctx: 1/0, category=ToolCategory.UTILITY)
        reg.register(tool)
        result = reg.call("crash")
        assert result.success is False
        assert "error" in result.error.lower() or "division" in result.error.lower()

    def test_call_not_found(self, reg):
        result = reg.call("non_existent")
        assert result.success is False

    def test_create_default_tools(self):
        registry = create_default_tools()
        assert isinstance(registry, ToolRegistry)
        all_tools = registry.list()
        assert len(all_tools) >= 5
        names = [t.name for t in all_tools]
        assert "calculate" in names
        assert "read_file" in names


# ─── AHSIntegration Tests ─────────────────────────────────────

class TestAHSIntegration:
    @pytest.fixture
    def ahs(self):
        inst = AHSIntegration()
        inst.initialize()
        yield inst
        inst.shutdown()

    def test_initialize(self, ahs):
        status = ahs.get_status()
        assert status["status"] == "running"
        assert "uptime" in status

    def test_process_empty_task(self, ahs):
        result = ahs.process("")
        assert result.get("response") is not None

    def test_process_simple(self, ahs):
        result = ahs.process("say hello")
        assert isinstance(result, dict)

    def test_get_status(self, ahs):
        status = ahs.get_status()
        assert status["version"] == "0.3.0"
        assert "components" in status

    def test_shutdown(self, ahs):
        ahs.shutdown()
        status = ahs.get_status()
        assert status["status"] == "stopped"

    def test_bootstrap(self):
        ahs = bootstrap()
        assert ahs is not None
        assert isinstance(ahs, AHSIntegration)
        ahs.shutdown()

    def test_events(self, ahs):
        events = []
        def handler(data):
            events.append(data)
        ahs.on("test_event", handler)
        ahs._emit("test_event", {"msg": "hello"})
        assert len(events) == 1
        assert events[0]["msg"] == "hello"

    def test_initialize_twice(self, ahs):
        result = ahs.initialize()
        assert result["status"] == "running"
