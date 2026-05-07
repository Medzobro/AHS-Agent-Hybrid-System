#!/usr/bin/env python3
"""
AHS - Multi-Agent System
=========================
إدارة وتنسيق الوكلاء الفرعيين (Sub-Agents) للعمل بالتوازي.

OpenClaw يدير وكلاء متعددين:
  - Hermes Agent: تفكير عميق
  - Code Agent: برمجة
  - Research Agent: بحث
  - Task Agent: مهام محددة
"""

import json, os, sys, time, uuid, threading, logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bridge.hermes_bridge import HermesBridge
from core.orchestrator import HybridOrchestrator, TaskType

logger = logging.getLogger("ahs.multiagent")


class AgentRole(Enum):
    """أدوار الوكلاء"""
    ORCHESTRATOR = "orchestrator"     # المنسق الرئيسي (OpenClaw)
    DEEP_THINKER = "deep_thinker"     # مفكر عميق (Hermes)
    CODER = "coder"                   # مبرمج
    RESEARCHER = "researcher"         # باحث
    EXECUTOR = "executor"             # منفذ
    CRITIC = "critic"                 # ناقد/مراجع
    LEARNER = "learner"               # متعلم


@dataclass
class AgentTask:
    """مهمة لوكيل"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: AgentRole = AgentRole.EXECUTOR
    description: str = ""
    input_data: Any = None
    skills: List[str] = field(default_factory=lambda: ["dogfood"])
    priority: int = 5  # 1-10
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 120


class AgentWorker:
    """
    وكيل عامل يمكنه تنفيذ المهام.
    كل وكيل يرتبط بدور محدد.
    """

    def __init__(self, role: AgentRole, name: Optional[str] = None):
        self.role = role
        self.name = name or f"agent-{role.value}-{uuid.uuid4().hex[:6]}"
        self.hermes = HermesBridge()
        self.current_task: Optional[AgentTask] = None
        self.stats = {"tasks_completed": 0, "tasks_failed": 0, "total_time": 0.0}

    def can_handle(self, task: AgentTask) -> bool:
        """هل هذا الوكيل مناسب للمهمة؟"""
        return task.role == self.role

    def execute(self, task: AgentTask) -> AgentTask:
        """تنفيذ مهمة"""
        task.status = "running"
        task.started_at = time.time()
        self.current_task = task

        try:
            if self.role == AgentRole.DEEP_THINKER:
                result = self._deep_think(task)
            elif self.role == AgentRole.CODER:
                result = self._code(task)
            elif self.role == AgentRole.RESEARCHER:
                result = self._research(task)
            elif self.role == AgentRole.CRITIC:
                result = self._critique(task)
            elif self.role == AgentRole.LEARNER:
                result = self._learn(task)
            else:
                result = self._execute(task)

            task.result = result
            task.status = "completed"
            self.stats["tasks_completed"] += 1

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.stats["tasks_failed"] += 1
            logger.error(f"Worker {self.name} failed: {e}")

        task.completed_at = time.time()
        elapsed = task.completed_at - (task.started_at or task.created_at)
        self.stats["total_time"] += elapsed
        self.current_task = None
        return task

    def _deep_think(self, task: AgentTask) -> str:
        """تفكير عميق عبر Hermes"""
        prompt = (
            f"فكر بعمق وحلل:\n{task.description}\n\n"
            f"قدم تحليلاً كاملاً مع أمثلة."
        )
        result = self.hermes.send_task(
            task=prompt,
            skills=",".join(task.skills),
            thinking_mode=True,
            timeout=task.timeout
        )
        if result.get("success"):
            resp = result.get("response", {})
            content = resp.get("content", "") or resp.get("content_raw", "") or ""
            reasoning = resp.get("reasoning", "")
            return f"[التفكير]\n{reasoning[:300]}\n\n[الرد]\n{content[:1000]}"
        return f"[فشل التفكير] {result.get('error')}"

    def _code(self, task: AgentTask) -> str:
        """كتابة كود"""
        result = self.hermes.send_task(
            task=f"اكتب كود Python:\n{task.description}\n\nقدم الكود كاملاً بين <code> tags",
            skills="dogfood",
            thinking_mode=True,
            timeout=task.timeout
        )
        return result.get("response", {}).get("content", "") or ""

    def _research(self, task: AgentTask) -> str:
        """بحث"""
        result = self.hermes.send_task(
            task=f"ابحث وقدم معلومات عن:\n{task.description}",
            skills="dogfood",
            thinking_mode=True,
            timeout=task.timeout
        )
        return result.get("response", {}).get("content", "") or ""

    def _critique(self, task: AgentTask) -> str:
        """مراجعة ونقد"""
        result = self.hermes.send_task(
            task=f"راجع ونقد:\n{task.description}\n\nقدم تحليلًا نقديًا بناءً",
            skills="dogfood",
            thinking_mode=True,
            timeout=task.timeout
        )
        return result.get("response", {}).get("content", "") or ""

    def _learn(self, task: AgentTask) -> str:
        """تعلم شيء جديد"""
        result = self.hermes.send_task(
            task=f"تعلم واشرح:\n{task.description}\n\nقدم ملخصاً تعليمياً",
            skills="dogfood",
            thinking_mode=True,
            timeout=task.timeout
        )
        return result.get("response", {}).get("content", "") or ""

    def _execute(self, task: AgentTask) -> str:
        """تنفيذ عام"""
        result = self.hermes.send_task(
            task=task.description,
            skills=",".join(task.skills),
            thinking_mode=True,
            timeout=task.timeout
        )
        return result.get("response", {}).get("content", "") or ""

    def summary(self) -> Dict:
        """ملخص الوكيل"""
        return {
            "name": self.name,
            "role": self.role.value,
            "busy": self.current_task is not None,
            "stats": self.stats,
            "current_task": self.current_task.description if self.current_task else None,
        }


class MultiAgentOrchestrator:
    """
    مدير الوكلاء المتعددين.
    يوزع المهام على الوكلاء المناسبين ويدير التبعيات.
    """

    def __init__(self):
        self.workers: Dict[str, AgentWorker] = {}
        self.task_queue: List[AgentTask] = []
        self.completed: List[AgentTask] = []
        self.failed: List[AgentTask] = []
        self.lock = threading.Lock()
        self.max_parallel = 3
        self.stats = {"tasks_created": 0, "tasks_completed": 0, "tasks_failed": 0}

    def register_worker(self, worker: AgentWorker):
        """تسجيل وكيل جديد"""
        with self.lock:
            self.workers[worker.name] = worker
            logger.info(f"Registered worker: {worker.name} ({worker.role.value})")

    def register_default_workers(self):
        """تسجيل الوكلاء الأساسيين"""
        workers = [
            AgentWorker(AgentRole.DEEP_THINKER, "hermes-thinker"),
            AgentWorker(AgentRole.CODER, "code-writer"),
            AgentWorker(AgentRole.RESEARCHER, "researcher"),
            AgentWorker(AgentRole.CRITIC, "code-critic"),
            AgentWorker(AgentRole.LEARNER, "skill-learner"),
        ]
        for w in workers:
            self.register_worker(w)

    def create_task(self, description: str, role: AgentRole = AgentRole.EXECUTOR,
                    priority: int = 5, skills: Optional[List[str]] = None,
                    depends_on: Optional[List[str]] = None) -> AgentTask:
        """إنشاء مهمة جديدة"""
        task = AgentTask(
            role=role,
            description=description,
            skills=skills or ["dogfood"],
            priority=priority,
            depends_on=depends_on or [],
        )
        with self.lock:
            self.task_queue.append(task)
            self.task_queue.sort(key=lambda t: -t.priority)
            self.stats["tasks_created"] += 1
        return task

    def find_worker(self, task: AgentTask) -> Optional[str]:
        """إيجاد وكيل مناسب للمهمة"""
        # ابحث عن وكيل غير مشغول بنفس الدور
        for name, worker in self.workers.items():
            if worker.can_handle(task) and worker.current_task is None:
                return name
        # إذا كلهم مشغولين، خذ أول وكيل بنفس الدور
        for name, worker in self.workers.items():
            if worker.can_handle(task):
                return name
        return None

    def run_all(self, timeout: int = 300) -> Dict:
        """تشغيل كل المهام في قائمة الانتظار"""
        start = time.time()
        running: Dict[str, AgentTask] = {}

        while (self.task_queue or running) and (time.time() - start < timeout):
            # إضافة مهام جديدة للعمال المتاحين
            while len(running) < self.max_parallel and self.task_queue:
                task = self.task_queue.pop(0)

                # تحقق من التبعيات
                deps_met = all(
                    any(d == c.id for c in self.completed)
                    for d in task.depends_on
                )
                if not deps_met:
                    # أعد المهمة لآخر القائمة
                    self.task_queue.append(task)
                    continue

                worker_name = self.find_worker(task)
                if worker_name:
                    running[task.id] = task
                    worker = self.workers[worker_name]

                    def _run(t=task, w=worker):
                        try:
                            result = w.execute(t)
                            with self.lock:
                                if result.status == "completed":
                                    self.completed.append(result)
                                    self.stats["tasks_completed"] += 1
                                else:
                                    self.failed.append(result)
                                    self.stats["tasks_failed"] += 1
                        except Exception as e:
                            t.status = "failed"
                            t.error = str(e)
                            with self.lock:
                                self.failed.append(t)
                                self.stats["tasks_failed"] += 1
                        finally:
                            running.pop(t.id, None)

                    thread = threading.Thread(target=_run, daemon=True)
                    thread.start()
                else:
                    # ما في وكيل متاح، أعد المهمة
                    self.task_queue.append(task)
                    break

            time.sleep(0.5)

        # انتظر كل المهام الجارية
        wait_start = time.time()
        while running and (time.time() - wait_start < 60):
            time.sleep(0.5)

        elapsed = time.time() - start
        return {
            "completed": len(self.completed),
            "failed": len(self.failed),
            "pending": len(self.task_queue),
            "elapsed": round(elapsed, 1),
            "tasks": [
                {"id": t.id, "role": t.role.value, "status": t.status,
                 "description": t.description[:50]}
                for t in self.completed + self.failed
            ],
            "stats": self.stats,
        }

    def run_parallel(self, descriptions: List[str]) -> Dict:
        """تشغيل مهام متعددة بالتوازي"""
        for desc in descriptions:
            self.create_task(desc)
        return self.run_all()

    def summary(self) -> Dict:
        """ملخص النظام متعدد الوكلاء"""
        return {
            "workers": {n: w.summary() for n, w in self.workers.items()},
            "queue": len(self.task_queue),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "stats": self.stats,
        }


if __name__ == "__main__":
    orchestrator = MultiAgentOrchestrator()
    orchestrator.register_default_workers()

    print("🧪 اختبار Multi-Agent:")
    r = orchestrator.run_parallel([
        "باختصار وش هو الـ AI Agent؟",
        "اكتب دالة Python تجمع رقمين",
    ])
    print(f"✅ مكتمل: {r['completed']}")
    print(f"❌ فاشل: {r['failed']}")
    print(f"⏱ {r['elapsed']}s")
    for t in r['tasks']:
        print(f"  [{t['status']}] {t['role']}: {t['description']}")
