#!/usr/bin/env python3
"""
AHS - Plugin System
====================
نظام الإضافات — توسيع قدرات AHS بإضافات خارجية.

Features:
  - Load plugins from directories
  - Auto-discovery
  - Lifecycle management (init, start, stop)
  - Extension points
  - Built-in plugins
"""

import json, os, sys, time, uuid, importlib, inspect, threading
from typing import Dict, List, Optional, Any, Callable, Type
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class PluginStatus(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    LOADED = "loaded"
    ERROR = "error"


class PluginPriority(Enum):
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4


@dataclass
class PluginMeta:
    """Plugin metadata"""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    requires: List[str] = field(default_factory=list)
    extension_points: List[str] = field(default_factory=list)
    priority: PluginPriority = PluginPriority.NORMAL
    tags: List[str] = field(default_factory=list)


class Plugin:
    """Base class for plugins — all plugins inherit from this"""

    meta = PluginMeta(name="base_plugin")

    def __init__(self):
        self.status = PluginStatus.DISABLED
        self.created_at = time.time()

    def on_load(self):
        """Called on load"""
        self.status = PluginStatus.LOADED

    def on_enable(self):
        """Called on enable"""
        self.status = PluginStatus.ENABLED

    def on_disable(self):
        """Called on disable"""
        self.status = PluginStatus.DISABLED

    def on_unload(self):
        """Called on unload"""
        self.status = PluginStatus.DISABLED

    def get_info(self) -> Dict:
        return {
            "name": self.meta.name,
            "version": self.meta.version,
            "description": self.meta.description,
            "author": self.meta.author,
            "status": self.status.value,
            "state": self.__class__.__name__,
        }


class PluginManager:
    """
    Plugin manager — discovers, loads, and manages all plugins.
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dirs = plugin_dirs or []
        self._lock = threading.Lock()
        self._hooks: Dict[str, List[Callable]] = {}

    def discover(self, directory: str) -> List[str]:
        """Discover plugins in directory"""
        found = []
        path = Path(directory)
        if not path.exists():
            return found

        for f in path.glob("*.py"):
            if f.name.startswith("_"):
                continue
            found.append(str(f))

        # مجلدات فرعية
        for d in path.iterdir():
            if d.is_dir() and (d / "__init__.py").exists():
                found.append(str(d))

        return found

    def load_plugin(self, plugin_path: str) -> Optional[Plugin]:
        """Load plugin from file"""
        try:
            path = Path(plugin_path)
            if path.is_file():
                spec = importlib.util.spec_from_file_location(
                    f"ahs_plugin_{path.stem}", path
                )
                if not spec or not spec.loader:
                    return None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # مجلد
                sys.path.insert(0, str(path.parent))
                module = importlib.import_module(f"ahs_plugin_{path.name}")

            # البحث عن كلاسات Plugin
            plugin_instances = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, Plugin) and
                    obj is not Plugin):
                    instance = obj()
                    instance.on_load()
                    plugin_instances.append(instance)

            if not plugin_instances:
                return None

            # التسجيل
            for inst in plugin_instances:
                with self._lock:
                    self.plugins[inst.meta.name] = inst

            return plugin_instances[0]

        except Exception as e:
            return None

    def load_all(self) -> Dict[str, str]:
        """Load all plugins from registered directories"""
        results = {}
        for directory in self.plugin_dirs:
            found = self.discover(directory)
            for plugin_path in found:
                name = Path(plugin_path).stem
                plugin = self.load_plugin(plugin_path)
                if plugin:
                    results[name] = "✅"
                else:
                    results[name] = "❌"
        return results

    def enable(self, name: str) -> bool:
        """Enable plugin"""
        plugin = self.plugins.get(name)
        if plugin and plugin.status == PluginStatus.LOADED:
            plugin.on_enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable plugin"""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.on_disable()
            return True
        return False

    def get(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)

    def list(self, status: Optional[PluginStatus] = None) -> List[Dict]:
        plugins = []
        for name, plugin in self.plugins.items():
            if status and plugin.status != status:
                continue
            plugins.append(plugin.get_info())
        return plugins

    def register_hook(self, hook_name: str, handler: Callable):
        """Register hook"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """Trigger hook"""
        for handler in self._hooks.get(hook_name, []):
            try:
                handler(*args, **kwargs)
            except Exception:
                pass

    def get_stats(self) -> Dict:
        count = len(self.plugins)
        enabled = sum(1 for p in self.plugins.values()
                     if p.status == PluginStatus.ENABLED)
        errors = sum(1 for p in self.plugins.values()
                    if p.status == PluginStatus.ERROR)
        return {
            "total": count,
            "enabled": enabled,
            "errors": errors,
            "hooks": len(self._hooks),
        }


# ====== Built-in plugins ======

class LogPlugin(Plugin):
    """Logging plugin — logs all activity"""
    meta = PluginMeta(
        name="log_plugin",
        version="1.0.0",
        description="Centralized logging for all AHS activity",
        author="AHS Team",
    )

    def __init__(self):
        super().__init__()
        self.log_file = None

    def on_enable(self):
        super().on_enable()
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / f"plugin_{int(time.time())}.log"

    def log(self, message: str, level: str = "INFO"):
        if self.log_file:
            line = f"[{time.strftime('%H:%M:%S')}] [{level}] {message}\n"
            self.log_file.write_text(
                self.log_file.read_text() + line if self.log_file.exists() else line
            )


class StatsPlugin(Plugin):
    """Statistics plugin — collects system stats"""
    meta = PluginMeta(
        name="stats_plugin",
        version="1.0.0",
        description="System statistics collection",
        author="AHS Team",
    )

    def __init__(self):
        super().__init__()
        self.metrics: Dict[str, List[float]] = {}

    def record(self, metric: str, value: float):
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(value)
        if len(self.metrics[metric]) > 1000:
            self.metrics[metric] = self.metrics[metric][-500:]

    def average(self, metric: str) -> float:
        values = self.metrics.get(metric, [])
        if not values:
            return 0.0
        return sum(values) / len(values)

    def report(self) -> Dict:
        return {
            name: {
                "avg": round(self.average(name), 2),
                "min": round(min(vals), 2) if vals else 0,
                "max": round(max(vals), 2) if vals else 0,
                "count": len(vals),
            }
            for name, vals in self.metrics.items()
        }


class BackupPlugin(Plugin):
    """Backup plugin"""
    meta = PluginMeta(
        name="backup_plugin",
        version="0.1.0",
        description="Automatic backup of critical data",
        author="AHS Team",
    )

    def __init__(self):
        super().__init__()
        self.backup_dir = Path("backups")
        self.last_backup: Optional[float] = None

    def on_enable(self):
        super().on_enable()
        self.backup_dir.mkdir(exist_ok=True)

    def backup_file(self, path: str) -> bool:
        try:
            src = Path(path)
            if not src.exists():
                return False
            ts = time.strftime("%Y%m%d_%H%M%S")
            dst = self.backup_dir / f"{src.stem}_{ts}{src.suffix}"
            dst.write_text(src.read_text())
            self.last_backup = time.time()
            return True
        except Exception:
            return False


if __name__ == "__main__":
    mgr = PluginManager()

    # Built-in plugins
    for plugin_cls in [LogPlugin, StatsPlugin, BackupPlugin]:
        inst = plugin_cls()
        inst.on_load()
        inst.on_enable()
        mgr.plugins[inst.meta.name] = inst

    print("📦 AHS Plugins:")
    for info in mgr.list():
        print(f"  [{info['status']}] {info['name']} v{info['version']}")
        print(f"    {info['description']}")

    print(f"\n📊 Stats: {mgr.get_stats()}")
    print("✅ Plugin system ready")
