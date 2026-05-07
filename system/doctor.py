#!/usr/bin/env python3
"""
AHS - System Health & Doctor
==============================
System Health Diagnosis — Check all components and ensure they are working.

Checks:
  - Hermes Gateway
  - API Keys
  - File System
  - Memory
  - Skills
  - Network
  - Performance
"""

import json, os, sys, time, subprocess, platform, socket
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil


@dataclass
class CheckResult:
    """Check result"""
    name: str
    status: str  # pass, fail, warn, error
    message: str
    details: Optional[Dict] = None
    duration: float = 0.0

    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "duration": round(self.duration, 3),
        }


class HealthCheck:
    """Health check for a specific component"""

    def __init__(self, name: str):
        self.name = name

    def run(self) -> CheckResult:
        raise NotImplementedError


class HermesGatewayCheck(HealthCheck):
    """Check Hermes Gateway"""

    def __init__(self):
        super().__init__("Hermes Gateway")

    def run(self) -> CheckResult:
        start = time.time()
        try:
            result = subprocess.run(
                ["pgrep", "-f", "hermes gateway"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                pids = result.stdout.strip().splitlines()
                return CheckResult(
                    name=self.name,
                    status="pass",
                    message=f"Gateway is running (PID: {', '.join(pids[:3])})",
                    details={"pids": pids, "count": len(pids)},
                    duration=time.time() - start,
                )
            return CheckResult(
                name=self.name, status="fail",
                message="Gateway is not running",
                duration=time.time() - start,
            )
        except Exception as e:
            return CheckResult(
                name=self.name, status="error",
                message=str(e), duration=time.time() - start,
            )


class ApiKeyCheck(HealthCheck):
    """Check API Keys"""

    def __init__(self):
        super().__init__("API Keys")

    def run(self) -> CheckResult:
        start = time.time()
        keys_found = []
        keys_missing = []
        env_file = "/data/.hermes/.env"

        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "API_KEY" in line or "TOKEN" in line:
                        if "=" in line:
                            key, val = line.split("=", 1)
                            status = "✅ Present" if val and len(val) > 10 else "⚠️ Empty"
                            keys_found.append(f"{key}: {status}")
                            keys_missing.append(key)

        if keys_found:
            return CheckResult(
                name=self.name, status="pass",
                message=f"Found {len(keys_found)} keys",
                details={"keys": keys_found},
                duration=time.time() - start,
            )
        return CheckResult(
            name=self.name, status="warn",
            message="No API keys found",
            duration=time.time() - start,
        )


class FileSystemCheck(HealthCheck):
    """Check File System"""

    def __init__(self):
        super().__init__("File System")

    def run(self) -> CheckResult:
        start = time.time()
        issues = []
        ok = []

        required_paths = [
            "core/orchestrator.py",
            "core/agent_loop.py",
            "bridge/hermes_bridge.py",
            "main.py",
            "skills/",
        ]

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for p in required_paths:
            full = os.path.join(base, p)
            if os.path.exists(full):
                ok.append(p)
            else:
                issues.append(f"Missing: {p}")

        # Project size
        total_size = 0
        total_files = 0
        for root, dirs, files in os.walk(base):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    total_files += 1

        return CheckResult(
            name=self.name,
            status="pass" if not issues else "warn",
            message=f"{total_files} files, {total_size:,} bytes",
            details={
                "total_files": total_files,
                "total_size": total_size,
                "present": ok,
                "issues": issues,
                "base_path": base,
            },
            duration=time.time() - start,
        )


class MemoryCheck(HealthCheck):
    """Check Memory and Disk"""

    def __init__(self):
        super().__init__("System Resources")

    def run(self) -> CheckResult:
        start = time.time()
        details = {}

        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            details = {
                "memory_total": f"{mem.total / (1024**3):.1f} GB",
                "memory_used": f"{mem.used / (1024**3):.1f} GB",
                "memory_percent": mem.percent,
                "disk_total": f"{disk.total / (1024**3):.1f} GB",
                "disk_free": f"{disk.free / (1024**3):.1f} GB",
                "disk_percent": disk.percent,
            }
            status = "pass" if mem.percent < 90 and disk.percent < 90 else "warn"
            msg = f"RAM {mem.percent}% | Disk {disk.percent}%"
        except ImportError:
            # Fallback without psutil
            statvfs = os.statvfs("/")
            disk_total = statvfs.f_frsize * statvfs.f_blocks
            disk_free = statvfs.f_frsize * statvfs.f_bfree
            disk_pct = (disk_total - disk_free) / disk_total * 100
            details = {
                "disk_total": f"{disk_total / (1024**3):.1f} GB",
                "disk_free": f"{disk_free / (1024**3):.1f} GB",
                "disk_percent": round(disk_pct, 1),
            }
            status = "pass" if disk_pct < 90 else "warn"
            msg = f"Disk {disk_pct:.1f}%"

        return CheckResult(
            name=self.name, status=status,
            message=msg, details=details,
            duration=time.time() - start,
        )


class NetworkCheck(HealthCheck):
    """Check Network and Connectivity"""

    def __init__(self):
        super().__init__("Network")

    def run(self) -> CheckResult:
        start = time.time()
        results = []
        endpoints = [
            ("DeepSeek API", "api.deepseek.com", 443),
            ("GitHub", "github.com", 443),
            ("PyPI", "pypi.org", 443),
        ]

        for name, host, port in endpoints:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((host, port))
                sock.close()
                results.append(f"{name} ✅")
            except Exception:
                results.append(f"{name} ❌")

        status = "pass" if all("✅" in r for r in results) else "warn"
        return CheckResult(
            name=self.name, status=status,
            message=", ".join(results),
            details={"endpoints": results},
            duration=time.time() - start,
        )


class PythonCheck(HealthCheck):
    """Check Python Environment"""

    def __init__(self):
        super().__init__("Python Environment")

    def run(self) -> CheckResult:
        start = time.time()
        required_modules = ["json", "os", "sys", "time", "uuid",
                            "threading", "pathlib", "typing", "subprocess"]

        missing = []
        for mod in required_modules:
            try:
                __import__(mod)
            except ImportError:
                missing.append(mod)

        details = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
            "required_modules_present": len(required_modules) - len(missing),
            "required_modules_total": len(required_modules),
        }

        if missing:
            return CheckResult(
                name=self.name, status="warn",
                message=f"Missing: {', '.join(missing)}",
                details=details, duration=time.time() - start,
            )
        return CheckResult(
            name=self.name, status="pass",
            message=f"Python {details['python_version']}",
            details=details, duration=time.time() - start,
        )


class PerformanceCheck(HealthCheck):
    """Check Performance"""

    def __init__(self):
        super().__init__("Performance")

    def run(self) -> CheckResult:
        start = time.time()
        perf_data = {}

        # JSON serialization speed
        test_data = {"key": "value" * 1000}
        json_start = time.time()
        for _ in range(100):
            json.dumps(test_data)
        perf_data["json_serialize"] = round((time.time() - json_start) / 100 * 1000, 2)

        # Calculation speed
        calc_start = time.time()
        for i in range(10000):
            _ = i * i + i / 2
        perf_data["calc_ops"] = f"{round((time.time() - calc_start) * 1000, 1)}ms"

        return CheckResult(
            name=self.name, status="pass",
            message=f"JSON: {perf_data['json_serialize']}ms, Calc OK",
            details=perf_data, duration=time.time() - start,
        )


class Doctor:
    """
    System Doctor — Runs all checks and provides a complete report.
    """

    def __init__(self):
        self.checks: List[HealthCheck] = [
            HermesGatewayCheck(),
            ApiKeyCheck(),
            FileSystemCheck(),
            MemoryCheck(),
            NetworkCheck(),
            PythonCheck(),
            PerformanceCheck(),
        ]

    def add_check(self, check: HealthCheck):
        self.checks.append(check)

    def diagnose(self) -> Dict:
        """Run all checks"""
        results = []
        start = time.time()

        for check in self.checks:
            try:
                result = check.run()
                results.append(result)
            except Exception as e:
                results.append(CheckResult(
                    name=check.name, status="error",
                    message=f"Check failed: {e}"
                ))

        elapsed = time.time() - start

        passed = sum(1 for r in results if r.passed())
        failed = sum(1 for r in results if r.status == "fail")
        warnings = sum(1 for r in results if r.status == "warn")

        overall = "pass" if failed == 0 else (
            "warn" if warnings > 0 else "fail"
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "overall": overall,
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "elapsed": round(elapsed, 2),
            },
            "checks": [r.to_dict() for r in results],
            "recommendations": self._recommendations(results),
        }

    def _recommendations(self, results: List[CheckResult]) -> List[str]:
        """Generate recommendations based on check results"""
        recs = []
        for r in results:
            if r.status == "fail":
                recs.append(f"🔴 {r.name}: {r.message}")
            elif r.status == "warn":
                recs.append(f"🟡 {r.name}: {r.message}")
        if not recs:
            recs.append("✅ System is in good condition")
        recs.append("💡 Tip: Run checks periodically for monitoring")
        return recs

    def summary_text(self) -> str:
        """Text report"""
        report = self.diagnose()
        s = report["summary"]

        lines = [
            "═════════════════════════════════",
            "  🏥 AHS System Health Report",
            "═════════════════════════════════",
            "",
            f"📅 {report['timestamp']}",
            f"⏱ {s['elapsed']}s",
            "",
            f"✅ Passed: {s['passed']}/{s['total']}",
            f"⚠️ Warnings: {s['warnings']}",
            f"❌ Failed: {s['failed']}",
            "",
            "━━━ Checks ━━━",
        ]

        for c in report["checks"]:
            icons = {"pass": "✅", "fail": "❌", "warn": "⚠️", "error": "🚨"}
            icon = icons.get(c["status"], "❓")
            lines.append(f"  {icon} {c['name']}: {c['message']}")

        lines.extend(["", "━━━ Recommendations ━━━"])
        lines.extend(f"  {r}" for r in report["recommendations"])
        lines.append("")

        return "\n".join(lines)


def quick_health() -> Dict:
    """Quick health check"""
    doctor = Doctor()
    return doctor.diagnose()


def print_health_report():
    """Print health report"""
    doctor = Doctor()
    print(doctor.summary_text())


if __name__ == "__main__":
    print_health_report()