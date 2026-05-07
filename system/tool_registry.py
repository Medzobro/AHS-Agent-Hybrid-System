#!/usr/bin/env python3
"""
AHS - Tool Registry
====================
سجل الأدوات المركزي — يدير الأدوات المتاحة للنظام الهجين.

الأدوات هي قدرات يمكن للـ Agent استخدامها:
  - FileTool: قراءة/كتابة ملفات
  - CodeTool: تشغيل وتنفيذ كود
  - SearchTool: بحث
  - MemoryTool: استدعاء الذاكرة
  - HermesTool: التواصل مع Hermes
  - WebTool: تصفح الإنترنت
"""

import json, os, sys, time, uuid, inspect, hashlib
from typing import Dict, List, Optional, Any, Callable, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import traceback


class ToolCategory(Enum):
    FILE = "file"             # أدوات ملفات
    CODE = "code"             # أدوات برمجة
    SEARCH = "search"         # أدوات بحث
    MEMORY = "memory"         # أدوات ذاكرة
    SYSTEM = "system"         # أدوات نظام
    COMMUNICATION = "comm"    # أدوات تواصل
    ANALYSIS = "analysis"     # أدوات تحليل
    UTILITY = "utility"       # أدوات مساعدة
    HERMES = "hermes"         # أدوات Hermes
    WEB = "web"               # أدوات ويب


@dataclass
class ToolSpec:
    """مواصفات الأداة"""
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    timeout: int = 30
    rate_limit: int = 0  # calls per minute, 0 = unlimited
    enabled: bool = True
    version: str = "1.0.0"
    author: str = "AHS"
    requires_hermes: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "version": self.version,
            "author": self.author,
            "parameters": self.parameters,
            "requires_hermes": self.requires_hermes,
        }


class ToolResult:
    """نتيجة تنفيذ أداة"""
    def __init__(self, success: bool, data: Any = None,
                 error: Optional[str] = None, duration: float = 0.0):
        self.success = success
        self.data = data
        self.error = error
        self.duration = duration
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": str(self.data)[:500] if self.data else None,
            "error": self.error,
            "duration": round(self.duration, 3),
        }

    @staticmethod
    def ok(data: Any = None) -> "ToolResult":
        return ToolResult(True, data=data)

    @staticmethod
    def fail(error: str) -> "ToolResult":
        return ToolResult(False, error=error)


class ToolRegistry:
    """
    السجل المركزي للأدوات — كل الأدوات مسجلة هنا.
    OpenClaw و Hermes يبحثان عن الأدوات من هذا السجل.
    """

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._call_history: List[Dict] = []
        self._call_counts: Dict[str, List[float]] = {}
        self.max_history = 1000

    def register(self, tool: ToolSpec):
        """تسجيل أداة جديدة"""
        if tool.name in self._tools:
            raise ValueError(f"الأداة '{tool.name}' مسجلة مسبقاً")
        self._tools[tool.name] = tool

    def register_many(self, tools: List[ToolSpec]):
        """تسجيل عدة أدوات"""
        for t in tools:
            self.register(t)

    def unregister(self, name: str):
        """إلغاء تسجيل أداة"""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[ToolSpec]:
        """الحصول على أداة بالاسم"""
        return self._tools.get(name)

    def list(self, category: Optional[ToolCategory] = None,
             enabled_only: bool = True) -> List[ToolSpec]:
        """عرض الأدوات المتاحة (اختياري حسب التصنيف)"""
        tools = self._tools.values()
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        if category:
            tools = [t for t in tools if t.category == category]
        return sorted(tools, key=lambda t: t.name)

    def search(self, query: str) -> List[ToolSpec]:
        """بحث في الأدوات"""
        query = query.lower()
        results = []
        for tool in self._tools.values():
            if (query in tool.name.lower() or
                query in tool.description.lower()):
                results.append(tool)
        return results

    def call(self, name: str, **kwargs) -> ToolResult:
        """استدعاء وتنفيذ أداة"""
        start = time.time()
        tool = self.get(name)

        if not tool:
            return ToolResult.fail(f"الأداة '{name}' غير موجودة")
        if not tool.enabled:
            return ToolResult.fail(f"الأداة '{name}' معطلة")

        # Rate limiting
        if tool.rate_limit > 0:
            now = time.time()
            calls = self._call_counts.get(name, [])
            calls = [c for c in calls if now - c < 60]
            if len(calls) >= tool.rate_limit:
                return ToolResult.fail(f"تجاوز حد الاستخدام: {tool.rate_limit}/دقيقة")
            calls.append(now)
            self._call_counts[name] = calls

        try:
            result = tool.handler(**kwargs)
            duration = time.time() - start
            tr = ToolResult.ok(result) if not isinstance(result, ToolResult) else result
            tr.duration = duration
            self._log_call(name, True, duration, kwargs)
            return tr
        except Exception as e:
            duration = time.time() - start
            self._log_call(name, False, duration, kwargs, str(e))
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _log_call(self, tool_name: str, success: bool,
                  duration: float, args: Dict, error: Optional[str] = None):
        """تسجيل استدعاء"""
        self._call_history.append({
            "tool": tool_name,
            "success": success,
            "duration": round(duration, 3),
            "args": {k: str(v)[:100] for k, v in args.items()},
            "error": error,
            "time": time.time(),
        })
        if len(self._call_history) > self.max_history:
            self._call_history = self._call_history[-self.max_history:]

    def get_stats(self) -> Dict:
        """إحصائيات استخدام الأدوات"""
        total = len(self._call_history)
        successful = sum(1 for c in self._call_history if c["success"])
        by_tool = {}
        for c in self._call_history:
            tn = c["tool"]
            if tn not in by_tool:
                by_tool[tn] = {"calls": 0, "success": 0, "total_time": 0.0}
            by_tool[tn]["calls"] += 1
            by_tool[tn]["success"] += 1 if c["success"] else 0
            by_tool[tn]["total_time"] += c["duration"]

        return {
            "total_tools": len(self._tools),
            "enabled_tools": sum(1 for t in self._tools.values() if t.enabled),
            "total_calls": total,
            "success_rate": round(successful / total * 100, 1) if total else 0,
            "by_tool": by_tool,
            "recent_calls": self._call_history[-10:],
        }


# ====== أدوات افتراضية ======

def _tool_read_file(filepath: str, max_chars: int = 5000) -> str:
    """قراءة ملف"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {filepath}")
    if not path.is_file():
        raise ValueError(f"ليس ملفاً: {filepath}")
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n... [مقتطع, {len(content)} حرف كلياً]"
    return content


def _tool_write_file(filepath: str, content: str, append: bool = False) -> str:
    """كتابة ملف"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    return f"تم الحفظ: {filepath} ({len(content)} حرف)"


def _tool_list_files(directory: str, pattern: str = "*") -> List[str]:
    """عرض محتويات مجلد"""
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"المجلد غير موجود: {directory}")
    files = list(path.glob(pattern))
    return [str(f.relative_to(path)) for f in files]


def _tool_calculate(expression: str) -> float:
    """حساب تعبير رياضي"""
    allowed = set("0123456789+-*/.()% ")
    if not all(c in allowed for c in expression):
        raise ValueError("تعبير غير صالح: يحتوي على محارف غير مسموحة")
    return eval(expression, {"__builtins__": {}}, {})


def _tool_json_parse(text: str) -> Dict:
    """تحليل JSON"""
    return json.loads(text)


def _tool_json_dumps(data: Any, pretty: bool = True) -> str:
    """تحويل إلى JSON"""
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, ensure_ascii=False)


def _tool_count_lines(filepath: str) -> Dict:
    """إحصاء أسطر ملف"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {filepath}")
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    return {
        "file": filepath,
        "total_lines": len(lines),
        "non_empty": len([l for l in lines if l.strip()]),
        "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*"))]),
        "chars": len(content),
    }


def _tool_hash_file(filepath: str, algorithm: str = "sha256") -> str:
    """حساب هاش لملف"""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _tool_uuid() -> str:
    """توليد UUID"""
    return uuid.uuid4().hex


def _tool_timestamp() -> Dict:
    """الحصول على الوقت الحالي"""
    now = time.time()
    return {
        "unix": now,
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
    }


def create_default_tools() -> ToolRegistry:
    """إنشاء السجل مع الأدوات الافتراضية"""
    registry = ToolRegistry()

    file_tools = [
        ToolSpec("read_file", "قراءة ملف نصي", ToolCategory.FILE,
                 _tool_read_file, {"filepath": "str", "max_chars": "int"}),
        ToolSpec("write_file", "كتابة أو إنشاء ملف", ToolCategory.FILE,
                 _tool_write_file, {"filepath": "str", "content": "str", "append": "bool"}),
        ToolSpec("list_files", "عرض محتويات مجلد", ToolCategory.FILE,
                 _tool_list_files, {"directory": "str", "pattern": "str"}),
        ToolSpec("count_lines", "إحصاء أسطر ملف", ToolCategory.FILE,
                 _tool_count_lines, {"filepath": "str"}),
        ToolSpec("hash_file", "حساب هاش ملف", ToolCategory.FILE,
                 _tool_hash_file, {"filepath": "str", "algorithm": "str"}),
    ]

    util_tools = [
        ToolSpec("calculate", "حساب تعبير رياضي آمن", ToolCategory.UTILITY,
                 _tool_calculate, {"expression": "str"}),
        ToolSpec("json_parse", "تحليل نص JSON", ToolCategory.UTILITY,
                 _tool_json_parse, {"text": "str"}),
        ToolSpec("json_dumps", "تحويل بيانات إلى JSON", ToolCategory.UTILITY,
                 _tool_json_dumps, {"data": "any", "pretty": "bool"}),
        ToolSpec("uuid", "توليد معرف فريد", ToolCategory.UTILITY,
                 _tool_uuid, {}),
        ToolSpec("timestamp", "الوقت الحالي", ToolCategory.UTILITY,
                 _tool_timestamp, {}),
    ]

    registry.register_many(file_tools + util_tools)
    return registry


def dump_tools_registry(registry: ToolRegistry) -> str:
    """تحويل سجل الأدوات إلى نص منظم"""
    lines = ["# 🛠️ سجل الأدوات - AHS Tool Registry", ""]
    for category in ToolCategory:
        tools = registry.list(category=category)
        if not tools:
            continue
        lines.append(f"## 📂 {category.value.upper()}")
        for t in tools:
            params = ", ".join(f"{k}: {v}" for k, v in t.parameters.items())
            lines.append(f"- **{t.name}**: {t.description} ({params})")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    reg = create_default_tools()
    print(dump_tools_registry(reg))

    print("\n🧪 اختبار الأدوات:")
    r1 = reg.call("calculate", expression="2 + 3 * 4")
    print(f"  calculate(2+3*4) = {r1.data} ✅" if r1.success else f"  ❌ {r1.error}")

    r2 = reg.call("uuid")
    print(f"  uuid() = {r2.data} ✅" if r2.success else f"  ❌ {r2.error}")

    r3 = reg.call("timestamp")
    print(f"  timestamp() = {r3.data} ✅" if r3.success else f"  ❌ {r3.error}")

    print(f"\n📊 إحصائيات: {reg.get_stats()['total_tools']} أداة, {reg.get_stats()['total_calls']} استدعاء")
