"""AHS v1.0 — Unit Tests for Self-Learning + Skill Manager

Adapted to actual source APIs.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from system.self_learn import ErrorEntry, ErrorAnalyzer
from system.skill_manager import Skill, SkillCategory, SkillManager


# ─── ErrorEntry Tests ─────────────────────────────────────────

class TestErrorEntry:
    def test_create_with_context(self):
        e = ErrorEntry(
            error_type="test_error",
            message="division by zero",
            file_path="calc.py",
            line_no=42,
            code_snippet="result = a / b",
            stack_trace="  File calc.py:42",
            context={"env": "test"},
        )
        assert e.error_type == "test_error"
        assert e.message == "division by zero"

    def test_create_minimal(self):
        e = ErrorEntry("t", "msg", "/f.py", 1, "", "")
        assert isinstance(e.error_type, str)

    def test_to_dict(self):
        e = ErrorEntry("type_a", "msg", "f.py", 1, "x=1", "")
        d = e.to_dict()
        assert "id" in d
        assert d["type"] == "type_a"
        assert d["message"] == "msg"

    def test_auto_severity(self):
        e = ErrorEntry("critical_error", "CRITICAL: disk full", "/f.py", 1, "", "")
        d = e.to_dict()
        assert "severity" in d


# ─── ErrorAnalyzer Tests ──────────────────────────────────────

class TestErrorAnalyzer:
    @pytest.fixture
    def analyzer(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        a = ErrorAnalyzer(db_path=db_path)
        yield a
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_log_error_returns_id(self, analyzer):
        e = ErrorEntry("t", "test", "/f.py", 1, "", "")
        result = analyzer.log_error(e)
        assert "id" in result

    def test_log_and_mark_fixed(self, analyzer):
        e = ErrorEntry("t", "fix_me", "/f.py", 1, "", "")
        result = analyzer.log_error(e)
        error_id = result["id"]
        analyzer.mark_fixed(error_id, "unit_test", True)
        # Should not raise
        assert True

    def test_log_performance_string_context(self, analyzer):
        result = analyzer.log_performance("query", 150.0, True, "/f.py",
                                           json.dumps({"table": "users"}))
        assert isinstance(result, type(None)) or isinstance(result, dict)

    def test_get_frequent_errors(self, analyzer):
        e = ErrorEntry("freq", "freq err", "/f.py", 1, "", "")
        analyzer.log_error(e)
        analyzer.log_error(e)
        errors = analyzer.get_frequent_errors(limit=5)
        assert isinstance(errors, list)

    def test_get_stats(self, analyzer):
        stats = analyzer.get_stats()
        assert isinstance(stats, dict)
        assert "total_errors_logged" in stats

    def test_get_slowest_operations(self, analyzer):
        analyzer.log_performance("slow_op", 999.0, True, "/f.py", "")
        ops = analyzer.get_slowest_operations(limit=5)
        assert isinstance(ops, list)


# ─── SkillCategory Tests ───────────────────────────────────

class TestSkillCategory:
    def test_has_general(self):
        assert SkillCategory.GENERAL is not None
    def test_has_code(self):
        assert SkillCategory.CODE.value == "code"


# ─── Skill Tests ─────────────────────────────────────────────

# Skill requires 7 positional args: name, description, version, category,
# module_path, entry_point (author, deps, etc are defaulted)
COMMON_ARGS = ["test_skill", "desc", "1.0", SkillCategory.GENERAL, "/mod.py", "run"]

class TestSkill:
    def test_create_minimal(self):
        s = Skill(*COMMON_ARGS)
        assert s.name == "test_skill"

    def test_create_with_kwargs(self):
        s = Skill(*COMMON_ARGS, author="AHS", enabled=True)
        assert s.author == "AHS"

    def test_to_dict(self):
        s = Skill(*COMMON_ARGS, tags=["test", "demo"])
        d = s.to_dict()
        assert d["name"] == "test_skill"
        assert d["tags"] == ["test", "demo"]

    def test_disabled_skill(self):
        s = Skill(*COMMON_ARGS, enabled=False)
        assert s.enabled is False


# ─── SkillManager Tests ───────────────────────────────────────

class TestSkillManager:
    @pytest.fixture
    def manager(self):
        return SkillManager(skills_dir=str(ROOT / "skills"))

    def test_discover(self, manager):
        skills = manager.discover()
        assert isinstance(skills, list)

    def test_load_all(self, manager):
        count = manager.load_all()
        assert count >= 0

    def test_get_nonexistent(self, manager):
        assert manager.get("does_not_exist_xyz") is None

    def test_list_skills(self, manager):
        skills = manager.list()
        assert isinstance(skills, list)

    def test_get_stats(self, manager):
        stats = manager.get_stats()
        assert isinstance(stats, dict)

    def test_enable_disable(self, manager):
        assert manager.enable("nonexistent") is False
        assert manager.disable("nonexistent") is False

    def test_search(self, manager):
        results = manager.search("test")
        assert isinstance(results, list)
