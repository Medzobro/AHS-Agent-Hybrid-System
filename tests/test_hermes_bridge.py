"""AHS v1.0 — Unit Tests for HermesBridge"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from bridge.hermes_bridge import HermesBridge


class TestHermesBridge:
    def test_create(self):
        bridge = HermesBridge()
        assert bridge is not None

    def test_status(self):
        bridge = HermesBridge()
        s = bridge.status()
        assert isinstance(s, dict)
        assert "http_available" in s or "mcp_available" in s

    def test_error_response(self):
        bridge = HermesBridge()
        err = bridge._error("test_code", "test message")
        assert isinstance(err, dict)
        assert "success" in err
        assert err.get("success") is False

    def test_double_init_safe(self):
        bridge = HermesBridge()
        bridge._check_mcp_module()
        assert True
