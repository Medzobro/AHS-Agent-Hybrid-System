#!/usr/bin/env python3
"""
AHS - Hermes Bridge
====================
Advanced bridge between OpenClaw and Hermes
Communicates via MCP protocol + subprocess with thinking mode
"""

import json
import os
import subprocess
import sys
import time
import select
from typing import Dict, List, Optional, Any


class HermesBridge:
    """
    Advanced bridge for communicating with Hermes.
    Supports:
    - Sending tasks with thinking mode (deepseek-reasoner)
    - Receiving responses
    - Session management
    - Activating specific skills
    """

    def __init__(self):
        self.hermes_path = os.path.expanduser("~/.local/bin/hermes")
        self.env = os.environ.copy()
        self.env["DEEPSEEK_API_KEY"] = "sk-95c57330681d43a5bcb1ac14613b6ae2"
        self.env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{self.env.get('PATH', '')}"
        self.session_dir = "/data/.hermes/sessions/"
        self.last_session: Optional[str] = None

    def _get_latest_session(self) -> Optional[str]:
        """Get the latest Hermes session (by modification time)"""
        try:
            sessions = [
                f for f in os.listdir(self.session_dir)
                if f.endswith(".json") and not f.startswith("session_cron")
            ]
            if sessions:
                # Latest by modification time
                sessions.sort(
                    key=lambda f: os.path.getmtime(os.path.join(self.session_dir, f)),
                    reverse=True
                )
                return sessions[0]
        except Exception:
            pass
        return None

    def send_task(
        self,
        task: str,
        skills: str = "dogfood",
        timeout: int = 120,
        thinking_mode: bool = True,
        context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send a task to Hermes with thinking mode.

        Args:
            task: The task
            skills: Activated skills
            timeout: Timeout in seconds
            thinking_mode: Enable thinking mode (deepseek-reasoner)

        Returns:
            Task result
        """
        # Record sessions before
        before_session = self._get_latest_session()

        # Build command
        cmd = [
            self.hermes_path, "chat",
            "--query", task,
            "--skills", skills,
        ]

        if thinking_mode:
            cmd.extend(["-m", "deepseek-reasoner"])

        try:
            # Run Hermes
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=timeout
            )

            # Wait a moment for session to be written
            time.sleep(2)

            # Get the latest session (not the old one)
            after_session = self._get_latest_session()
            
            # Extract session ID from output if no new session found
            session_to_read = after_session or before_session
            if after_session and after_session == before_session:
                # Try to extract from stdout
                import re
                match = re.search(r'--resume (\S+)', result.stdout)
                if match:
                    session_to_read = match.group(1) + '.json'

            response_data = self._extract_response(session_to_read)

            # If empty and stdout has a response, use it
            if not response_data.get('content') and result.stdout:
                # Extract response after the last ╭─ 
                lines = result.stdout.split('\n')
                in_response = False
                response_lines = []
                for line in lines:
                    if '╭─ ╚' in line or 'Hermes' in line:
                        in_response = True
                        continue
                    if in_response:
                        if '╰─' in line or 'Resume' in line or 'Session:' in line:
                            break
                        cleaned = line.strip().strip('│').strip()
                        if cleaned:
                            response_lines.append(cleaned)
                
                if response_lines:
                    # In case of quick response, content is in stdout
                    response_data['content_raw'] = '\n'.join(response_lines)

            return {
                "success": True,
                "session": session_to_read,
                "response": response_data,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout expired",
                "session": self._get_latest_session(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _extract_response(self, session_file: Optional[str]) -> Dict:
        """Extract response from session"""
        if not session_file:
            return {"content": "", "reasoning": ""}

        session_path = os.path.join(self.session_dir, session_file)
        if not os.path.exists(session_path):
            # Try searching for the latest session
            session_file = self._get_latest_session()
            if session_file:
                session_path = os.path.join(self.session_dir, session_file)
            else:
                return {"content": "", "reasoning": ""}

        if not os.path.exists(session_path):
            return {"content": "", "reasoning": ""}

        try:
            with open(session_path) as f:
                data = json.load(f)

            messages = data.get("messages", [])
            assistant_msgs = [
                m for m in messages if m.get("role") == "assistant"
            ]

            if not assistant_msgs:
                return {"content": "", "reasoning": ""}

            last = assistant_msgs[-1]
            content = last.get("content", "") or ""
            reasoning = last.get("reasoning_content", "") or ""

            return {
                "content": content,
                "reasoning": reasoning,
                "tool_calls": last.get("tool_calls", []),
            }

        except Exception as e:
            return {"error": str(e)}

    def analyze_with_hermes(self, task: str) -> Dict:
        """Deep analysis with Hermes (thinking mode)"""
        enhanced_task = (
            f"[Deep analysis with thinking]\n"
            f"Task: {task}\n\n"
            f"Analyze this task deeply. Think step by step.\n"
            f"Provide: analysis → proposed solution → execution plan"
        )
        return self.send_task(
            task=enhanced_task,
            skills="systematic-debugging,dogfood",
            thinking_mode=True,
        )


# Test
if __name__ == "__main__":
    bridge = HermesBridge()

    print("🧪 Testing Hermes bridge...")
    result = bridge.send_task(
        "Just say: The bridge is working",
        thinking_mode=True
    )

    if result["success"]:
        response = result.get("response", {})
        print(f"✅ Response: {response.get('content', '')[:200]}")
        if response.get("reasoning"):
            print(f"🤔 Thinking: {response['reasoning'][:200]}")
    else:
        print(f"❌ Error: {result.get('error')}")