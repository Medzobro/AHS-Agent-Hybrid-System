#!/usr/bin/env python3
"""
AHS - Hermes Bridge
====================
جسر متطور بين OpenClaw و Hermes
يتواصل عبر MCP protocol + subprocess مع وضع التفكير
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
    جسر متطور للتواصل مع Hermes.
    يدعم:
    - إرسال مهام مع وضع التفكير (deepseek-reasoner)
    - استقبال الردود
    - إدارة الجلسات
    - تفعيل مهارات محددة
    """

    def __init__(self):
        self.hermes_path = os.path.expanduser("~/.local/bin/hermes")
        self.env = os.environ.copy()
        self.env["DEEPSEEK_API_KEY"] = "sk-95c57330681d43a5bcb1ac14613b6ae2"
        self.env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{self.env.get('PATH', '')}"
        self.session_dir = "/data/.hermes/sessions/"
        self.last_session: Optional[str] = None

    def _get_latest_session(self) -> Optional[str]:
        """الحصول على آخر جلسة Hermes (حسب وقت التعديل)"""
        try:
            sessions = [
                f for f in os.listdir(self.session_dir)
                if f.endswith(".json") and not f.startswith("session_cron")
            ]
            if sessions:
                # أحدثها حسب وقت التعديل
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
        إرسال مهمة إلى Hermes مع وضع التفكير.

        Args:
            task: المهمة
            skills: المهارات المفعلة
            timeout: مهلة الانتظار بالثواني
            thinking_mode: تشغيل وضع التفكير (deepseek-reasoner)

        Returns:
            نتيجة المهمة
        """
        # سجل الـ sessions قبل
        before_session = self._get_latest_session()

        # بناء الأمر
        cmd = [
            self.hermes_path, "chat",
            "--query", task,
            "--skills", skills,
        ]

        if thinking_mode:
            cmd.extend(["-m", "deepseek-reasoner"])

        try:
            # تشغيل Hermes
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=timeout
            )

            # انتظر لحظة عشان session يكتب
            time.sleep(2)

            # نجيب أحدث session (غير الجلسة القديمة)
            after_session = self._get_latest_session()
            
            # نستخرج الـ session ID من المخرجات إذا ما لقينا session جديد
            session_to_read = after_session or before_session
            if after_session and after_session == before_session:
                # حاول نستخرج من stdout
                import re
                match = re.search(r'--resume (\S+)', result.stdout)
                if match:
                    session_to_read = match.group(1) + '.json'

            response_data = self._extract_response(session_to_read)

            # إذا فارغ والـ stdout فيه رد، نستخدمه
            if not response_data.get('content') and result.stdout:
                # نستخرج الرد من بعد آخر ╭─ 
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
                    # في حالة الرد السريع، المحتوى موجود في stdout
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
                "error": "انتهت المهلة الزمنية",
                "session": self._get_latest_session(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _extract_response(self, session_file: Optional[str]) -> Dict:
        """استخراج الرد من الجلسة"""
        if not session_file:
            return {"content": "", "reasoning": ""}

        session_path = os.path.join(self.session_dir, session_file)
        if not os.path.exists(session_path):
            # جرب البحث عن آخر session
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
        """تحليل عميق مع Hermes (وضع التفكير)"""
        enhanced_task = (
            f"[تحليل عميق مع التفكير]\n"
            f"المهمة: {task}\n\n"
            f"حلل هذه المهمة بعمق. فكر خطوة بخطوة.\n"
            f"قدم: تحليل → حل مقترح → خطة تنفيذ"
        )
        return self.send_task(
            task=enhanced_task,
            skills="systematic-debugging,dogfood",
            thinking_mode=True,
        )


# اختبار
if __name__ == "__main__":
    bridge = HermesBridge()

    print("🧪 اختبار جسر Hermes...")
    result = bridge.send_task(
        "قل فقط: الجسر شغال",
        thinking_mode=True
    )

    if result["success"]:
        response = result.get("response", {})
        print(f"✅ الرد: {response.get('content', '')[:200]}")
        if response.get("reasoning"):
            print(f"🤔 التفكير: {response['reasoning'][:200]}")
    else:
        print(f"❌ خطأ: {result.get('error')}")
