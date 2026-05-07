#!/usr/bin/env python3
"""
AHS - Event System
===================
نظام الأحداث — إدارة الاتصالات غير المتزامنة بين المكونات.

Features:
  - Central Event Bus
  - Synchronous and async events
  - Filters and subscriptions
  - Event history
  - Pub/Sub patterns
"""

import json, os, sys, time, uuid, threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Event in the system"""
    type: str
    data: Any = None
    source: str = "system"
    priority: EventPriority = EventPriority.NORMAL
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "data": str(self.data)[:200],
        }


class EventSubscription:
    """Subscribe to a specific event"""
    def __init__(self, event_type: str, handler: Callable,
                 priority: EventPriority = EventPriority.NORMAL,
                 filter_fn: Optional[Callable] = None,
                 name: Optional[str] = None):
        self.id = uuid.uuid4().hex[:8]
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.filter_fn = filter_fn
        self.name = name or handler.__name__
        self.active = True
        self.call_count = 0
        self.error_count = 0

    def should_handle(self, event: Event) -> bool:
        if not self.active:
            return False
        if self.filter_fn and not self.filter_fn(event):
            return False
        return True


class EventBus:
    """
    Central event bus — all components communicate through it.

    الأنماط:
      - emit: Emit event لمشتركيه
      - on: اشتراك في حدث
      - once: اشتراك لمرة واحدة
      - off: Unsubscribe
    """

    def __init__(self):
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._history: List[Event] = []
        self._wildcard_subs: List[EventSubscription] = []
        self.max_history = 500
        self._lock = threading.Lock()
        self._stats = {"emitted": 0, "handled": 0, "errors": 0}

    def on(self, event_type: str, handler: Callable,
           priority: EventPriority = EventPriority.NORMAL,
           filter_fn: Optional[Callable] = None,
           name: Optional[str] = None) -> str:
        """Subscribe to event"""
        subscription = EventSubscription(event_type, handler, priority, filter_fn, name)
        with self._lock:
            if event_type == "*":
                self._wildcard_subs.append(subscription)
            else:
                if event_type not in self._subscriptions:
                    self._subscriptions[event_type] = []
                self._subscriptions[event_type].append(subscription)
        return subscription.id

    def once(self, event_type: str, handler: Callable) -> str:
        """One-time subscription"""
        def wrapper(event: Event):
            handler(event)
            self.off(sub_id)
        sub_id = self.on(event_type, wrapper, name=f"{handler.__name__}_once")
        return sub_id

    def off(self, subscription_id: str):
        """Unsubscribe"""
        with self._lock:
            for subs in self._subscriptions.values():
                for sub in subs:
                    if sub.id == subscription_id:
                        sub.active = False
                        return
            for sub in self._wildcard_subs:
                if sub.id == subscription_id:
                    sub.active = False
                    return

    def emit(self, event_type: str, data: Any = None,
             source: str = "system",
             priority: EventPriority = EventPriority.NORMAL,
             metadata: Optional[Dict] = None) -> Event:
        """Emit event"""
        event = Event(
            type=event_type,
            data=data,
            source=source,
            priority=priority,
            metadata=metadata or {},
        )

        with self._lock:
            self._stats["emitted"] += 1
            self._history.append(event)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history:]

            # جمع المشتركين
            handlers = []
            handlers.extend(self._subscriptions.get(event_type, []))
            handlers.extend(self._subscriptions.get("*", []))
            handlers.extend(self._wildcard_subs)

            # ترتيب حسب الأولوية
            handlers.sort(key=lambda s: s.priority.value, reverse=True)

        # تنفيذ
        for sub in handlers:
            if not sub.should_handle(event):
                continue
            try:
                sub.handler(event)
                sub.call_count += 1
                with self._lock:
                    self._stats["handled"] += 1
            except Exception:
                sub.error_count += 1
                with self._lock:
                    self._stats["errors"] += 1

        return event

    def emit_async(self, event_type: str, data: Any = None,
                   source: str = "system") -> Event:
        """Emit event غير متزامن"""
        event = self.emit(event_type, data, source)
        return event

    def get_history(self, event_type: Optional[str] = None,
                    limit: int = 20) -> List[Event]:
        """Get event history"""
        if event_type:
            events = [e for e in self._history if e.type == event_type]
        else:
            events = list(self._history)
        return events[-limit:]

    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._history.clear()

    def subscription_count(self) -> int:
        """Subscription count"""
        count = len(self._wildcard_subs)
        for subs in self._subscriptions.values():
            count += len(subs)
        return count

    def get_stats(self) -> Dict:
        """Statistics"""
        return {
            **self._stats,
            "subscriptions": self.subscription_count(),
            "history_size": len(self._history),
            "event_types": list(self._subscriptions.keys()),
        }


# ====== Standard event types ======

class SystemEvents:
    """أحداث النظام القياسية"""
    # دورة الحياة
    INITIALIZED = "system.initialized"
    SHUTDOWN = "system.shutdown"
    ERROR = "system.error"
    WARNING = "system.warning"

    # المهام
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Hermes
    HERMES_CALL = "hermes.call"
    HERMES_RESPONSE = "hermes.response"
    HERMES_ERROR = "hermes.error"

    # الأدوات
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    TOOL_ERROR = "tool.error"

    # الذاكرة
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # المهارات
    SKILL_LOADED = "skill.loaded"
    SKILL_EXECUTED = "skill.executed"
    SKILL_ERROR = "skill.error"

    # المستخدم
    USER_MESSAGE = "user.message"
    USER_COMMAND = "user.command"
    USER_QUERY = "user.query"


# ====== Event Logger ======

class EventLogger:
    """Records events for debugging and monitoring"""
    def __init__(self, bus: EventBus, log_file: Optional[str] = None):
        self.bus = bus
        self.log_file = log_file
        self.log: List[Dict] = []

        bus.on("*", self._on_event, name="event_logger")

    def _on_event(self, event: Event):
        entry = {
            "time": time.strftime("%H:%M:%S", time.localtime(event.timestamp)),
            "type": event.type,
            "source": event.source,
            "data": str(event.data)[:100],
        }
        self.log.append(entry)
        if len(self.log) > 1000:
            self.log = self.log[-500:]

        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception:
                pass

    def get_log(self, event_type: Optional[str] = None,
                limit: int = 50) -> List[Dict]:
        if event_type:
            return [e for e in self.log if e["type"] == event_type][-limit:]
        return self.log[-limit:]

    def summary(self) -> str:
        """Quick summary"""
        types = {}
        for entry in self.log:
            t = entry["type"]
            types[t] = types.get(t, 0) + 1

        lines = ["📋 Event Log Summary", ""]
        for t, count in sorted(types.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {t}: {count}")
        lines.append(f"\n  Total: {len(self.log)} events")
        return "\n".join(lines)


# ====== أمثلة ======

class MessageHandler:
    """Example: user message handler"""
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.history: List[str] = []

        bus.on(SystemEvents.USER_MESSAGE, self.on_message, name="user_msg_handler")
        bus.on(SystemEvents.USER_COMMAND, self.on_command, name="user_cmd_handler")

    def on_message(self, event: Event):
        self.history.append(f"Msg: {event.data}")
        self.bus.emit("message.processed", {
            "text": event.data,
            "length": len(str(event.data)),
        }, source="message_handler")

    def on_command(self, event: Event):
        self.history.append(f"Cmd: {event.data}")
        self.bus.emit("command.processed", {
            "command": event.data,
        }, source="message_handler")


class TaskMonitor:
    """Example: task monitor"""
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.active_tasks: Set[str] = set()
        self.completed: int = 0
        self.failed: int = 0

        bus.on(SystemEvents.TASK_STARTED, self.on_start)
        bus.on(SystemEvents.TASK_COMPLETED, self.on_complete)
        bus.on(SystemEvents.TASK_FAILED, self.on_fail)

    def on_start(self, event: Event):
        task_id = event.data.get("id", "?") if isinstance(event.data, dict) else "?"
        self.active_tasks.add(task_id)

    def on_complete(self, event: Event):
        task_id = event.data.get("id", "?") if isinstance(event.data, dict) else "?"
        self.active_tasks.discard(task_id)
        self.completed += 1

    def on_fail(self, event: Event):
        task_id = event.data.get("id", "?") if isinstance(event.data, dict) else "?"
        self.active_tasks.discard(task_id)
        self.failed += 1

    def summary(self) -> Dict:
        return {
            "active": len(self.active_tasks),
            "completed": self.completed,
            "failed": self.failed,
        }


if __name__ == "__main__":
    bus = EventBus()
    handler = MessageHandler(bus)
    monitor = TaskMonitor(bus)
    logger = EventLogger(bus)

    # Simulate events
    bus.emit(SystemEvents.USER_MESSAGE, "مرحبا", source="test")
    bus.emit(SystemEvents.USER_COMMAND, "help", source="test")
    bus.emit(SystemEvents.TASK_STARTED, {"id": "task1"}, source="test")
    bus.emit(SystemEvents.TASK_COMPLETED, {"id": "task1"}, source="test")

    print("=== Event Stats ===")
    print(bus.get_stats())
    print()
    print("=== Log ===")
    print(logger.summary())
