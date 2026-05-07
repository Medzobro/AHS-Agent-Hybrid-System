#!/usr/bin/env python3
"""
AHS - Task Scheduler
=====================
جدولة وتنظيم المهام — تشغيل مهام مجدولة ومتكررة.

المميزات:
  - جدولة مهام بفواصل زمنية
  - مهام متكررة (cron-like)
  - مهام بموعد محدد
  - إدارة التبعيات
  - تاريخ التنفيذ
"""

import json, os, sys, time, uuid, threading, heapq
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


class TaskStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduledTask:
    """مهمة مجدولة"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    handler: Optional[Callable] = None
    interval_seconds: float = 0.0
    max_runs: int = 0  # 0 = غير محدود
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    next_run: float = 0.0
    last_run: Optional[float] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    total_duration: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def is_due(self) -> bool:
        return time.time() >= self.next_run

    @property
    def average_duration(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.total_duration / self.run_count

    @property
    def success_rate(self) -> float:
        total = self.run_count + self.error_count
        if total == 0:
            return 1.0
        return self.run_count / total

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "interval": self.interval_seconds,
            "status": self.status.value,
            "priority": self.priority.value,
            "runs": self.run_count,
            "errors": self.error_count,
            "success_rate": round(self.success_rate * 100, 1),
            "avg_duration": round(self.average_duration, 2),
            "next_run": datetime.fromtimestamp(self.next_run).isoformat() if self.next_run else None,
            "last_run": datetime.fromtimestamp(self.last_run).isoformat() if self.last_run else None,
        }


class Scheduler:
    """
    جدولة المهام — تشغيل مهام في الخلفية بفواصل زمنية.
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._history: List[Dict] = []
        self.max_history = 200

    def add_task(self, name: str, handler: Callable,
                 interval_seconds: float = 60.0,
                 description: str = "",
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_runs: int = 0,
                 tags: Optional[List[str]] = None,
                 start_now: bool = True) -> str:
        """إضافة مهمة مجدولة"""
        task = ScheduledTask(
            name=name,
            description=description or f"Task: {name}",
            handler=handler,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
            priority=priority,
            next_run=time.time() if start_now else time.time() + interval_seconds,
            tags=tags or [],
        )
        with self._lock:
            self._tasks[task.id] = task
        return task.id

    def remove_task(self, task_id: str) -> bool:
        """إزالة مهمة"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
                del self._tasks[task_id]
                return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.next_run)

    def pause_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.SCHEDULED:
            task.status = TaskStatus.PENDING
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.SCHEDULED
            task.next_run = time.time()
            return True
        return False

    def start(self):
        """تشغيل الجدولة في خلفية"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """إيقاف الجدولة"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        """الحلقة الرئيسية للجدولة"""
        while self._running:
            now = time.time()
            due_tasks = []

            with self._lock:
                for task in self._tasks.values():
                    if task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.SCHEDULED
                    if task.is_due and task.status == TaskStatus.SCHEDULED:
                        if task.max_runs > 0 and task.run_count >= task.max_runs:
                            task.status = TaskStatus.COMPLETED
                            continue
                        task.status = TaskStatus.RUNNING
                        due_tasks.append(task)

            for task in due_tasks:
                thread = threading.Thread(
                    target=self._execute_task,
                    args=(task,),
                    daemon=True,
                )
                thread.start()

            time.sleep(1)

    def _execute_task(self, task: ScheduledTask):
        """تنفيذ مهمة واحدة"""
        start = time.time()

        try:
            if task.handler:
                result = task.handler()
            else:
                result = None

            task.run_count += 1
            task.status = TaskStatus.SCHEDULED
            task.last_run = time.time()
            task.total_duration += time.time() - start
            task.next_run = time.time() + task.interval_seconds
            task.last_error = None

            self._log_execution(task.id, True, time.time() - start, result)

        except Exception as e:
            task.error_count += 1
            task.status = TaskStatus.SCHEDULED
            task.last_run = time.time()
            task.last_error = str(e)
            task.next_run = time.time() + task.interval_seconds

            self._log_execution(task.id, False, time.time() - start, str(e))

    def _log_execution(self, task_id: str, success: bool,
                       duration: float, result: Any):
        entry = {
            "task_id": task_id,
            "success": success,
            "duration": round(duration, 2),
            "time": datetime.now().isoformat(),
            "result": str(result)[:200],
        }
        self._history.append(entry)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def get_history(self, task_id: Optional[str] = None,
                    limit: int = 20) -> List[Dict]:
        if task_id:
            return [h for h in self._history if h["task_id"] == task_id][-limit:]
        return self._history[-limit:]

    def get_stats(self) -> Dict:
        """إحصائيات الجدولة"""
        tasks = list(self._tasks.values())
        total_runs = sum(t.run_count for t in tasks)
        total_errors = sum(t.error_count for t in tasks)
        active = sum(1 for t in tasks if t.status == TaskStatus.SCHEDULED)

        return {
            "total_tasks": len(tasks),
            "active_tasks": active,
            "running": self._running,
            "total_runs": total_runs,
            "total_errors": total_errors,
            "total_duration_hours": round(
                sum(t.total_duration for t in tasks) / 3600, 2
            ),
        }


# ====== أمثلة ======

def example_hourly_task():
    """مهمة مثال: تعمل كل ساعة"""
    return f"تم التنفيذ في {datetime.now().isoformat()}"


def example_daily_task():
    """مهمة مثال: تعمل كل 24 ساعة"""
    return f"Daily task at {datetime.now().isoformat()}"


if __name__ == "__main__":
    scheduler = Scheduler()

    # إضافة مهام
    scheduler.add_task(
        "example_hourly",
        example_hourly_task,
        interval_seconds=3600,
        description="مهمة كل ساعة",
        tags=["example"],
    )

    scheduler.add_task(
        "example_daily",
        example_daily_task,
        interval_seconds=86400,
        description="مهمة يومية",
        priority=TaskPriority.LOW,
        tags=["example", "daily"],
    )

    print("📋 Scheduler Tasks:")
    for task in scheduler.list_tasks():
        print(f"  [{task.status.value}] {task.name}")
        print(f"    Interval: {task.interval_seconds}s")
        print(f"    Description: {task.description}")

    print(f"\n📊 Stats: {scheduler.get_stats()}")
    print("✅ Scheduler module ready")
