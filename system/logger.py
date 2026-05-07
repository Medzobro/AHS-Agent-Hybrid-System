#!/usr/bin/env python3
"""
AHS - Logging System
=====================
نظام تسجيل شامل — يسجل كل شيء في النظام.

المميزات:
  - تسجيل بملفات
  - تسجيل بالذاكرة (للتشغيل السريع)
  - مستويات: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - تصدير وتحميل
  - فلاتر وبحث
"""

import json, os, sys, time, logging, traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_string(cls, name: str) -> "LogLevel":
        name = name.upper()
        for level in cls:
            if level.name == name:
                return level
        return cls.INFO

    @classmethod
    def from_int(cls, value: int) -> "LogLevel":
        for level in cls:
            if level.value == value:
                return level
        return cls.INFO


@dataclass
class LogEntry:
    """إدخال سجل واحد"""
    timestamp: float = field(default_factory=time.time)
    level: LogLevel = LogLevel.INFO
    component: str = "system"
    message: str = ""
    data: Any = None
    traceback: Optional[str] = None
    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])

    @property
    def time_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def level_icon(self) -> str:
        icons = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🚨",
        }
        return icons.get(self.level, "📝")

    def to_dict(self) -> Dict:
        return {
            "time": self.timestamp,
            "level": self.level.name,
            "component": self.component,
            "message": self.message,
            "data": str(self.data)[:500] if self.data else None,
        }

    def to_text(self) -> str:
        return f"[{self.time_str}] [{self.level.name:8}] [{self.component}] {self.message}"


class LogStorage:
    """تخزين السجلات"""

    def __init__(self, max_entries: int = 1000):
        self.entries: List[LogEntry] = []
        self.max_entries = max_entries

    def add(self, entry: LogEntry):
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries // 2:]

    def search(self, query: str = "",
               level: Optional[LogLevel] = None,
               component: Optional[str] = None,
               limit: int = 50) -> List[LogEntry]:
        results = self.entries
        if query:
            results = [e for e in results if query.lower() in e.message.lower()]
        if level:
            results = [e for e in results if e.level.value >= level.value]
        if component:
            results = [e for e in results if e.component == component]
        return results[-limit:]

    def export(self, path: str, format: str = "json"):
        data = [e.to_dict() for e in self.entries]
        if format == "json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif format == "text":
            with open(path, "w") as f:
                for e in self.entries:
                    f.write(e.to_text() + "\n")

    def clear(self):
        self.entries.clear()

    @property
    def count(self) -> int:
        return len(self.entries)

    def stats(self) -> Dict:
        levels = {}
        components = {}
        for e in self.entries:
            levels[e.level.name] = levels.get(e.level.name, 0) + 1
            components[e.component] = components.get(e.component, 0) + 1
        return {
            "total": self.count,
            "by_level": levels,
            "by_component": components,
        }


class AHSLogger:
    """
    المسجل الرئيسي — يسجل كل شيء في النظام.

    الاستخدام:
      logger = AHSLogger()
      logger.info("System started", component="system")
      logger.error("Failed", component="hermes", data=error)
    """

    def __init__(self, name: str = "ahs",
                 level: LogLevel = LogLevel.INFO,
                 log_to_console: bool = True,
                 log_to_file: Optional[str] = None):
        self.name = name
        self.level = level
        self.storage = LogStorage()
        self.file_handler: Optional[FilePath] = None
        self.log_to_console = log_to_console
        self.handlers: List[Callable[[LogEntry], None]] = []

        if log_to_file:
            self.set_log_file(log_to_file)

    def set_log_file(self, path: str):
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.file_handler = path
        except Exception:
            self.file_handler = None

    def set_level(self, level: LogLevel):
        self.level = level

    def add_handler(self, handler: Callable[[LogEntry], None]):
        self.handlers.append(handler)

    def _log(self, level: LogLevel, message: str,
             component: str = "system", data: Any = None):
        if level.value < self.level.value:
            return

        entry = LogEntry(
            level=level,
            component=component,
            message=str(message),
            data=data,
            traceback=traceback.format_exc() if level in (LogLevel.ERROR, LogLevel.CRITICAL) else None,
        )

        # تخزين
        self.storage.add(entry)

        # طباعة
        if self.log_to_console:
            print(entry.to_text())

        # ملف
        if self.file_handler:
            try:
                with open(self.file_handler, "a") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            except Exception:
                pass

        # handlers
        for handler in self.handlers:
            try:
                handler(entry)
            except Exception:
                pass

    def debug(self, message: str, component: str = "system", data: Any = None):
        self._log(LogLevel.DEBUG, message, component, data)

    def info(self, message: str, component: str = "system", data: Any = None):
        self._log(LogLevel.INFO, message, component, data)

    def warning(self, message: str, component: str = "system", data: Any = None):
        self._log(LogLevel.WARNING, message, component, data)

    def error(self, message: str, component: str = "system", data: Any = None):
        self._log(LogLevel.ERROR, message, component, data)

    def critical(self, message: str, component: str = "system", data: Any = None):
        self._log(LogLevel.CRITICAL, message, component, data)

    def search(self, query: str = "", **kwargs) -> List[LogEntry]:
        return self.storage.search(query, **kwargs)

    def export(self, path: str, format: str = "json"):
        self.storage.export(path, format)

    def get_stats(self) -> Dict:
        return self.storage.stats()

    def print_summary(self):
        stats = self.get_stats()
        print(f"\n📊 Logger Stats: {stats['total']} entries")
        print(f"  Levels: {stats['by_level']}")
        print(f"  Components: {stats['by_component']}")
        print(f"  Level: {self.level.name}")


# ====== أمثلة ======

def create_default_logger(log_dir: str = "logs") -> AHSLogger:
    """إنشاء المسجل الافتراضي"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "ahs.log")
    return AHSLogger(
        name="ahs",
        level=LogLevel.INFO,
        log_to_console=False,
        log_to_file=log_file,
    )


class LoggerAdapter:
    """محوّل: يربط الـ Logger مع المكونات المختلفة"""

    def __init__(self, logger: AHSLogger, component: str):
        self.logger = logger
        self.component = component

    def debug(self, msg: str, data=None): self.logger.debug(msg, self.component, data)
    def info(self, msg: str, data=None): self.logger.info(msg, self.component, data)
    def warning(self, msg: str, data=None): self.logger.warning(msg, self.component, data)
    def error(self, msg: str, data=None): self.logger.error(msg, self.component, data)
    def critical(self, msg: str, data=None): self.logger.critical(msg, self.component, data)


if __name__ == "__main__":
    logger = AHSLogger("test", level=LogLevel.DEBUG, log_to_console=True)

    # محاكاة تسجيل
    logger.debug("Starting debug test", component="test")
    logger.info("System initialized", component="system", data={"version": "0.2.0"})
    logger.warning("Memory usage high", component="system", data={"usage": "85%"})
    logger.error("API call failed", component="hermes")
    logger.critical("Out of memory!", component="system")

    print("\n📊 Stats:")
    print(logger.get_stats())
    print("\n✅ Logger ready")
