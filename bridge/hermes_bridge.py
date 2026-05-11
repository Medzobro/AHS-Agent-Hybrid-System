#!/usr/bin/env python3
"""
AHS - Hermes Bridge (MCP v6)
==============================
Real-time bridge using MCP protocol.
Replaces the old subprocess chat with direct MCP tool calls.
"""

import json
import os
import subprocess
import sys
import time
import re
from typing import Dict, List, Optional, Any

# Add workspace to path for openclaw_mcp_bridge
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, WORKSPACE)

from dotenv import load_dotenv

# Load .env if exists
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)


class HermesBridge:
    """
    MCP v6 Bridge to Hermes AI.
    Uses the OpenClaw ↔ Hermes MCP protocol for two-way communication.
    
    Modes:
      1. MCP Tool Call (preferred) — uses hermes_send() from openclaw_mcp_bridge
      2. hermes CLI (fallback) — when MCP bridge is unreachable
    """

    def __init__(self):
        self.hermes_path = os.environ.get("HERMES_PATH") or os.path.expanduser("~/.local/bin/hermes")
        self.env = os.environ.copy()
        api_key = os.environ.get("DEEPSEEK_API_KEY") or ""
        if api_key:
            self.env["DEEPSEEK_API_KEY"] = api_key
        local_bin = os.path.expanduser('~/.local/bin')
        self.env["PATH"] = f"{local_bin}:{self.env.get('PATH', '')}"
        self.last_response: Optional[str] = None
        self.last_reasoning: Optional[str] = None
        self.mcp_available = False
        self._mcp_bridge = None
        self.mcp_tools: Dict[str, Any] = {}
        self._check_mcp()
        self._discover_mcp_tools()

    def _check_mcp(self):
        """Check if MCP bridge module is available"""
        try:
            from openclaw_mcp_bridge import hermes_send
            self._mcp_bridge = hermes_send
            self.mcp_available = True
        except ImportError:
            self.mcp_available = False

    def _discover_mcp_tools(self):
        """Discover available MCP tools from Hermes"""
        try:
            import subprocess
            result = subprocess.run(
                [self.hermes_path, "mcp", "list"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.mcp_tools["list"] = result.stdout
        except Exception:
            pass

    def send_task(
        self,
        task: str,
        skills: str = "dogfood",
        timeout: int = 120,
        thinking_mode: bool = True,
        context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send a task to Hermes.
        
        Priority:
          1. MCP HTTP Bridge (fastest, localhost:18900)
          2. MCP Tool Call (Python bridge)
          3. CLI subprocess (stable fallback)
        """
        # 1. Try HTTP Bridge
        try:
            return self._send_via_http(task, timeout)
        except Exception:
            pass
        
        # 2. Try MCP
        if self.mcp_available:
            try:
                return self._send_via_mcp(task, timeout)
            except Exception as e:
                self.mcp_available = False

        # 3. Fallback to CLI
        return self._send_via_cli(task, skills, timeout, thinking_mode)

    def _send_via_http(self, task: str, timeout: int) -> Dict:
        """Send via AHS MCP HTTP Bridge"""
        import urllib.request
        
        data = json.dumps({"task": task, "mode": "hybrid"}).encode()
        req = urllib.request.Request(
            "http://localhost:18900/task",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
        
        if result.get("success"):
            return {
                "success": True,
                "method": "mcp_http",
                "response": {
                    "content": result.get("response", ""),
                    "mode": result.get("mode", "hybrid"),
                    "elapsed": result.get("elapsed", 0),
                },
                "elapsed": result.get("elapsed", 0),
            }
        return {"success": False, "method": "mcp_http", "error": result.get("error", "Unknown")}

    def _send_via_mcp(self, task: str, timeout: int) -> Dict:
        """Send via MCP Python bridge"""
        try:
            response = self._mcp_bridge(task)
            
            # Parse response
            content = str(response) if response else ""
            
            # Extract thinking content if present
            reasoning = ""
            if "Thinking:" in content:
                parts = content.split("Thinking:", 1)
                if len(parts) > 1:
                    rest = parts[1]
                    if "Response:" in rest:
                        reasoning, content = rest.split("Response:", 1)
                    else:
                        content = parts[0]
                        reasoning = rest

            self.last_response = content
            self.last_reasoning = reasoning

            return {
                "success": True,
                "method": "mcp",
                "response": {
                    "content": content.strip(),
                    "reasoning": reasoning.strip(),
                    "tool_calls": [],
                },
                "elapsed": 0.5,
            }
        except Exception as e:
            return {
                "success": False,
                "method": "mcp",
                "error": str(e),
            }

    def _send_via_cli(self, task: str, skills: str, timeout: int, thinking: bool) -> Dict:
        """Send via hermes CLI subprocess (stable fallback)"""
        cmd = [self.hermes_path, "chat", "--query", task, "--skills", skills]
        if thinking:
            cmd.extend(["-m", "deepseek-reasoner"])

        try:
            start = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=timeout
            )
            elapsed = time.time() - start

            stdout = result.stdout or ""
            stderr = result.stderr or ""

            # Parse CLI output
            content, reasoning = self._parse_cli_output(stdout, stderr)

            self.last_response = content
            self.last_reasoning = reasoning

            return {
                "success": True,
                "method": "cli",
                "response": {
                    "content": content,
                    "reasoning": reasoning,
                    "content_raw": stdout,
                    "tool_calls": [],
                },
                "return_code": result.returncode,
                "elapsed": round(elapsed, 1),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "method": "cli",
                "error": f"Timeout expired after {timeout}s",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "method": "cli",
                "error": f"hermes CLI not found at {self.hermes_path}. Install via: pip install hermes-ai",
            }
        except Exception as e:
            return {
                "success": False,
                "method": "cli",
                "error": str(e),
            }

    def _parse_cli_output(self, stdout: str, stderr: str) -> tuple:
        """Parse CLI output to extract content and reasoning"""
        content = ""
        reasoning = ""

        if not stdout:
            return content, reasoning

        # Try to extract response from structured terminal output
        lines = stdout.split('\n')
        in_response = False
        response_lines = []
        reasoning_lines = []

        for line in lines:
            clean = line.strip().strip('│').strip()

            # Detect thinking/reasoning markers
            if '思考' in line or '🤔' in line or 'Thinking:' in line:
                in_response = False
                continue
            if '回应' in line or '📤' in line or 'Response:' in line:
                in_response = True
                continue
            if '╰─' in line or 'Session:' in line or 'Resume with' in line:
                break

            if in_response:
                if clean:
                    response_lines.append(clean)
            else:
                if clean and len(clean) > 10:
                    reasoning_lines.append(clean)

        # If structured parsing failed, use raw output
        if response_lines:
            content = '\n'.join(response_lines)
        else:
            content = stdout[:2000]

        if reasoning_lines:
            reasoning = '\n'.join(reasoning_lines)

        return content, reasoning

    def analyze_with_hermes(self, task: str) -> Dict:
        """Deep analysis with thinking mode"""
        return self.send_task(
            task=f"Analyze deeply: {task}\nProvide: analysis → solution → plan",
            thinking_mode=True,
        )

    def status(self) -> Dict:
        """Bridge status"""
        return {
            "hermes_connected": self.mcp_available or bool(self._check_cli_available()),
            "mcp_available": self.mcp_available,
            "last_response_length": len(self.last_response or ""),
            "last_reasoning_length": len(self.last_reasoning or ""),
        }

    def _check_cli_available(self) -> bool:
        """Check if hermes CLI is available"""
        return os.path.isfile(self.hermes_path) and os.access(self.hermes_path, os.X_OK)


# Test
if __name__ == "__main__":
    bridge = HermesBridge()
    print(f"🔌 MCP Available: {bridge.mcp_available}")
    print(f"🔌 CLI Available: {bridge._check_cli_available()}")
    
    if bridge.mcp_available:
        print("\n🧪 Testing MCP bridge...")
        result = bridge._send_via_mcp("Say: AHS MCP Bridge is alive!", 30)
        print(f"✅ MCP: {result['success']}")
        if result['success']:
            print(f"📤 {result['response']['content'][:200]}")
    
    if not bridge.mcp_available and bridge._check_cli_available():
        print("\n🧪 Testing CLI bridge...")
        result = bridge._send_via_cli("Say: AHS CLI Bridge is alive!", "dogfood", 30, True)
        print(f"✅ CLI: {result['success']}")
        if result['success']:
            print(f"📤 {result['response']['content'][:200]}")
    
    print("\n📊 Status:", json.dumps(bridge.status(), indent=2))
