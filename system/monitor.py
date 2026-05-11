#!/usr/bin/env python3
"""
AHS - Monitoring System
========================
نظام المراقبة — يراقب أداء وصحة النظام.

Features:
  - Real-time monitoring
  - Performance statistics
  - Alertات عند المشاكل
  - Periodic reports
  - Metrics storage
"""

import json, os, sys, time, threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


@dataclass
class Metric:
    """Single metric"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict = field(default_factory=dict)
    source: str = "ahs"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "tags": self.tags,
            "source": self.source,
        }


@dataclass
class Alert:
    """Alert"""
    metric: str
    value: float
    threshold: float
    direction: str  # above / below
    time: float = field(default_factory=time.time)
    message: str = ""
    severity: str = "warning"  # info, warning, critical

    def to_dict(self) -> Dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "direction": self.direction,
            "message": self.message,
            "severity": self.severity,
            "time": datetime.fromtimestamp(self.time).isoformat(),
        }


class MetricsCollector:
    """Metrics collector"""

    def __init__(self, max_entries: int = 1000):
        self._metrics: Dict[str, deque] = {}
        self._max_entries = max_entries

    def record(self, name: str, value: float, **tags):
        """Record metric"""
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self._max_entries)
        self._metrics[name].append(Metric(name=name, value=value, tags=tags))

    def get(self, name: str, limit: int = 100) -> List[Metric]:
        if name not in self._metrics:
            return []
        return list(self._metrics[name])[-limit:]

    def latest(self, name: str) -> Optional[Metric]:
        metrics = self.get(name, 1)
        return metrics[0] if metrics else None

    def average(self, name: str, since: Optional[float] = None) -> float:
        metrics = self.get(name)
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        if not metrics:
            return 0.0
        return sum(m.value for m in metrics) / len(metrics)

    def min(self, name: str) -> float:
        metrics = self.get(name)
        if not metrics:
            return 0.0
        return min(m.value for m in metrics)

    def max(self, name: str) -> float:
        metrics = self.get(name)
        if not metrics:
            return 0.0
        return max(m.value for m in metrics)

    def percentile(self, name: str, pct: float) -> float:
        metrics = self.get(name)
        if not metrics:
            return 0.0
        values = sorted(m.value for m in metrics)
        idx = int(len(values) * pct / 100)
        return values[min(idx, len(values) - 1)]

    def all_names(self) -> List[str]:
        return list(self._metrics.keys())

    def summary(self) -> Dict:
        return {
            name: {
                "count": len(metrics),
                "latest": metrics[-1].value if metrics else None,
                "avg": round(self.average(name), 2),
                "min": round(self.min(name), 2),
                "max": round(self.max(name), 2),
                "p95": round(self.percentile(name, 95), 2),
            }
            for name, metrics in self._metrics.items()
        }


class Monitor:
    """
    Main monitoring system.
    """

    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts: List[Alert] = []
        self._thresholds: Dict[str, Dict] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alert_handlers: List[Callable] = []

    def set_threshold(self, metric: str, warning: float,
                      critical: float, direction: str = "above"):
        """تعيين حد إنذار"""
        self._thresholds[metric] = {
            "warning": warning,
            "critical": critical,
            "direction": direction,
        }

    def check_threshold(self, name: str, value: float):
        """التحقق من الحدود"""
        threshold = self._thresholds.get(name)
        if not threshold:
            return

        direction = threshold["direction"]
        triggered = False

        if direction == "above":
            if value >= threshold["critical"]:
                self._add_alert(name, value, threshold["critical"],
                                "above", "critical")
                triggered = True
            elif value >= threshold["warning"]:
                self._add_alert(name, value, threshold["warning"],
                                "above", "warning")
                triggered = True
        elif direction == "below":
            if value <= threshold["critical"]:
                self._add_alert(name, value, threshold["critical"],
                                "below", "critical")
                triggered = True
            elif value <= threshold["warning"]:
                self._add_alert(name, value, threshold["warning"],
                                "below", "warning")
                triggered = True

    def _add_alert(self, metric: str, value: float, threshold: float,
                   direction: str, severity: str):
        alert = Alert(
            metric=metric,
            value=value,
            threshold=threshold,
            direction=direction,
            severity=severity,
            message=f"{metric} = {value:.1f} ({threshold:.1f})",
        )
        self.alerts.append(alert)
        if len(self.alerts) > 200:
            self.alerts = self.alerts[-100:]

        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

    def on_alert(self, handler: Callable):
        """تسجيل معالج الAlertات"""
        self._alert_handlers.append(handler)

    def record(self, name: str, value: float, **tags):
        """Record metric مع التحقق من الحدود"""
        self.metrics.record(name, value, **tags)
        self.check_threshold(name, value)

    def record_execution(self, name: str, duration: float, success: bool):
        """Record execution (useful for tasks)"""
        self.record(f"{name}.duration", duration)
        self.record(f"{name}.success", 1.0 if success else 0.0)
        self.metrics.record(f"{name}.total", 1.0, success=str(success))

    def start_auto(self, interval: float = 60.0):
        """تشغيل المراقبة التلقائية"""
        self._running = True
        self._thread = threading.Thread(
            target=self._auto_loop,
            args=(interval,),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

    def _auto_loop(self, interval: float):
        while self._running:
            try:
                self._collect_system_metrics()
            except Exception:
                pass
            time.sleep(interval)

    def _collect_system_metrics(self):
        """جمع مقاييس النظام"""
        import resource
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            self.record("system.cpu", usage.ru_utime + usage.ru_stime)
            self.record("system.memory", usage.ru_maxrss)
            self.record("system.ctx_switches", usage.ru_nvcsw + usage.ru_nivcsw)
        except Exception:
            pass

    def get_report(self) -> Dict:
        """تقرير كامل"""
        recent_alerts = [a.to_dict() for a in self.alerts[-20:]]
        return {
            "metrics": self.metrics.summary(),
            "active_thresholds": self._thresholds,
            "recent_alerts": recent_alerts,
            "alert_count": len(self.alerts),
            "is_running": self._running,
        }

    def print_report(self):
        """طباعة التقرير"""
        report = self.get_report()
        print("\n📊 **Monitoring Report**")
        print(f"\n  Metrics ({len(report['metrics'])}):")
        for name, summary in list(report['metrics'].items())[:10]:
            print(f"    {name}: avg={summary['avg']}, "
                  f"latest={summary['latest']}, "
                  f"count={summary['count']}")

        if report['recent_alerts']:
            print(f"\n  🚨 Alerts ({len(report['recent_alerts'])} recent):")
            for a in report['recent_alerts'][-5:]:
                icon = "🔴" if a['severity'] == 'critical' else "🟡"
                print(f"    {icon} {a['message']}")

        print(f"\n  Running: {report['is_running']}")


# ====== Thresholds Predefined ======

class DefaultThresholds:
    """Default thresholds"""
    @staticmethod
    def apply(monitor: Monitor):
        monitor.set_threshold("hermes.duration", 30, 60, "above")
        monitor.set_threshold("system.memory", 500, 1000, "above")
        monitor.set_threshold("system.cpu", 10, 30, "above")
        monitor.set_threshold("tools.success", 80, 50, "below")


if __name__ == "__main__":
    monitor = Monitor()
    DefaultThresholds.apply(monitor)

    # Simulate metrics
    for i in range(10):
        monitor.record("test.metric", i * 10, test="simulation")
        monitor.record("hermes.duration", 5 + i * 3)

    print("📊 Monitor Report:")
    monitor.print_report()

    # محاكاة Alert
    monitor.record("hermes.duration", 65)  # → critical alert
    print("\n🚨 After alert:")
    monitor.print_report()

    print("\n✅ Monitor ready")
