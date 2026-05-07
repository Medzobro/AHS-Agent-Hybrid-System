#!/usr/bin/env python3
"""
AHS - Utilities & Helpers
===========================
أدوات مساعدة متنوعة للنظام.

Features:
  - Text processing
  - Data validation
  - Format conversion
  - Statistics
  - File helpers
  - Date/time utilities
"""

import json, os, sys, time, math, re, hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter


# =========================
#  Text Utilities
# =========================

class TextUtils:
    """Text processing tools"""

    ARABIC_CHARS = set("ابتثجحخدذرزسشصضطظعغفقكلمنهويءؤإأآةىپچڤڨڭ")

    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text"""
        if not text or len(text) <= max_length:
            return text or ""
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def word_count(text: str) -> int:
        """Word count"""
        return len(text.split())

    @staticmethod
    def char_count(text: str, count_spaces: bool = False) -> int:
        """Character count"""
        if count_spaces:
            return len(text)
        return len(text.replace(" ", ""))

    @staticmethod
    def line_count(text: str) -> int:
        """Line count"""
        return len(text.splitlines())

    @staticmethod
    def contains_arabic(text: str) -> bool:
        """Does text contain Arabic?"""
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F':
                return True
        return False

    @staticmethod
    def contains_english(text: str) -> bool:
        """Does text contain English?"""
        for char in text:
            if char.isascii() and char.isalpha():
                return True
        return False

    @staticmethod
    def remove_extra_spaces(text: str) -> str:
        """Remove extra spaces"""
        return ' '.join(text.split())

    @staticmethod
    def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
        """Extract code blocks from text"""
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return [(lang.strip(), code.strip()) for lang, code in matches]

    @staticmethod
    def extract_links(text: str) -> List[str]:
        """Extract links"""
        pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        return re.findall(pattern, text)

    @staticmethod
    def word_frequency(text: str, top: int = 10) -> List[Tuple[str, int]]:
        """Most frequent words"""
        words = re.findall(r'\w+', text.lower())
        return Counter(words).most_common(top)

    @staticmethod
    def similarity(text1: str, text2: str) -> float:
        """Text similarity (Jaccard)"""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)

    @staticmethod
    def wrap(text: str, width: int = 80) -> str:
        """Wrap text (word wrap)"""
        words = text.split()
        lines = []
        current = []
        current_len = 0
        for word in words:
            if current_len + len(word) + len(current) > width:
                lines.append(' '.join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word)
        if current:
            lines.append(' '.join(current))
        return '\n'.join(lines)

    @staticmethod
    def center(text: str, width: int = 80, fill: str = " ") -> str:
        """Center text"""
        return text.center(width, fill)


# =========================
#  Data Utilities
# =========================

class DataUtils:
    """Data processing tools"""

    @staticmethod
    def safe_get(data: Dict, *keys, default: Any = None) -> Any:
        """Safe nested value access"""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current

    @staticmethod
    def batch_process(items: List, batch_size: int = 10) -> List[List]:
        """Split list into batches"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    @staticmethod
    def deduplicate(items: List, key: Optional[Callable] = None) -> List:
        """Remove duplicates"""
        seen = set()
        result = []
        for item in items:
            k = key(item) if key else item
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    @staticmethod
    def group_by(items: List, key_fn: Callable) -> Dict:
        """Group items by key"""
        groups = {}
        for item in items:
            key = key_fn(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups

    @staticmethod
    def flatten(nested: List) -> List:
        """Flatten nested list"""
        result = []
        for item in nested:
            if isinstance(item, list):
                result.extend(DataUtils.flatten(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def deep_merge(base: Dict, overlay: Dict, overwrite: bool = True) -> Dict:
        """Deep merge two dicts"""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.deep_merge(result[key], value, overwrite)
            elif key not in result or overwrite:
                result[key] = value
        return result

    @staticmethod
    def filter_dict(d: Dict, keys: List[str]) -> Dict:
        """Filter dict by keys"""
        return {k: d[k] for k in keys if k in d}

    @staticmethod
    def rename_keys(d: Dict, mapping: Dict[str, str]) -> Dict:
        """Rename keys"""
        return {mapping.get(k, k): v for k, v in d.items()}

    @staticmethod
    def to_json(obj: Any, pretty: bool = True) -> str:
        """Convert to JSON"""
        indent = 2 if pretty else None
        return json.dumps(obj, indent=indent, ensure_ascii=False, default=str)

    @staticmethod
    def from_json(text: str) -> Any:
        """Parse JSON"""
        return json.loads(text)

    @staticmethod
    def to_table(data: List[Dict], headers: Optional[List[str]] = None) -> str:
        """Convert list to text table"""
        if not data:
            return ""
        if not headers:
            headers = list(data[0].keys())

        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
            for row in data:
                val = str(row.get(header, ""))
                col_widths[header] = max(col_widths[header], len(val))

        lines = []
        # Header
        header_line = " | ".join(
            h.ljust(col_widths[h]) for h in headers
        )
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Rows
        for row in data:
            line = " | ".join(
                str(row.get(h, "")).ljust(col_widths[h]) for h in headers
            )
            lines.append(line)

        return "\n".join(lines)


# =========================
#  Time Utilities
# =========================

class TimeUtils:
    """Time and date tools"""

    @staticmethod
    def now() -> float:
        return time.time()

    @staticmethod
    def now_iso() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def timestamp_to_iso(ts: float) -> str:
        return datetime.fromtimestamp(ts).isoformat()

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in readable way"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds/60:.1f}m"
        return f"{seconds/3600:.1f}h"

    @staticmethod
    def format_date(ts: Optional[float] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        dt = datetime.fromtimestamp(ts) if ts else datetime.now()
        return dt.strftime(fmt)

    @staticmethod
    def time_ago(ts: float) -> str:
        """Time ago"""
        diff = time.time() - ts
        if diff < 60:
            return f"منذ {int(diff)} ثانية"
        if diff < 3600:
            return f"منذ {int(diff/60)} دقيقة"
        if diff < 86400:
            return f"منذ {int(diff/3600)} ساعة"
        return f"منذ {int(diff/86400)} يوم"

    @staticmethod
    def human_readable_size(bytes_count: int) -> str:
        """Human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"


# =========================
#  Statistics Utilities
# =========================

class StatsUtils:
    """Statistical tools"""

    @staticmethod
    def mean(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def median(values: List[float]) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]

    @staticmethod
    def mode(values: List) -> Any:
        if not values:
            return None
        counter = Counter(values)
        return counter.most_common(1)[0][0]

    @staticmethod
    def min_max(values: List[float]) -> Tuple[float, float]:
        if not values:
            return (0.0, 0.0)
        return (min(values), max(values))

    @staticmethod
    def std_dev(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        avg = StatsUtils.mean(values)
        variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def percentile(values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        index = int(len(sorted_vals) * pct / 100)
        return sorted_vals[min(index, len(sorted_vals) - 1)]

    @staticmethod
    def distribution(values: List[float], bins: int = 10) -> List[int]:
        """توزيع القيم"""
        if not values:
            return []
        min_v, max_v = min(values), max(values)
        if min_v == max_v:
            return [len(values)]
        bin_size = (max_v - min_v) / bins
        hist = [0] * bins
        for v in values:
            idx = min(int((v - min_v) / bin_size), bins - 1)
            hist[idx] += 1
        return hist


# =========================
#  File Utilities
# =========================

class FileUtils:
    """File tools"""

    @staticmethod
    def safe_read(path: str, encoding: str = "utf-8",
                  max_size: int = 10 * 1024 * 1024) -> Optional[str]:
        """Safe file reading"""
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return None
            if path_obj.stat().st_size > max_size:
                return None
            return path_obj.read_text(encoding=encoding)
        except Exception:
            return None

    @staticmethod
    def safe_write(path: str, content: str, encoding: str = "utf-8") -> bool:
        """Safe file writing"""
        try:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(content, encoding=encoding)
            return True
        except Exception:
            return False

    @staticmethod
    def get_size(path: str) -> int:
        """File or directory size"""
        path_obj = Path(path)
        if not path_obj.exists():
            return 0
        if path_obj.is_file():
            return path_obj.stat().st_size
        total = 0
        for f in path_obj.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total

    @staticmethod
    def find_files(directory: str, pattern: str = "*.py",
                   recursive: bool = True) -> List[str]:
        """Find files"""
        path = Path(directory)
        if not path.exists():
            return []
        glob_fn = path.rglob if recursive else path.glob
        return [str(f.relative_to(path)) for f in glob_fn(pattern) if f.is_file()]

    @staticmethod
    def get_extension(path: str) -> str:
        return Path(path).suffix.lower()

    @staticmethod
    def get_stem(path: str) -> str:
        return Path(path).stem


# =========================
#  Security Utilities
# =========================

class SecurityUtils:
    """Security tools"""

    @staticmethod
    def hash_string(text: str, algorithm: str = "sha256") -> str:
        h = hashlib.new(algorithm)
        h.update(text.encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def hash_file(path: str, algorithm: str = "sha256") -> Optional[str]:
        try:
            h = hashlib.new(algorithm)
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """تنظيف اسم الملف"""
        return re.sub(r'[^\w\-_\. ]', '_', name)

    @staticmethod
    def is_safe_path(path: str, allowed_dirs: Optional[List[str]] = None) -> bool:
        """Safe path check"""
        resolved = os.path.realpath(path)
        if allowed_dirs:
            for ad in allowed_dirs:
                if resolved.startswith(os.path.realpath(ad)):
                    return True
            return False
        return True

    @staticmethod
    def is_safe_expression(expr: str) -> bool:
        """التحقق من أمان التعبير الرياضي"""
        allowed = set("0123456789+-*/.()% ")
        return all(c in allowed for c in expr)


if __name__ == "__main__":
    print("🧪 Utilities Test")

    # Text
    text = "مرحبا بكم في AHS Agent Hybrid System"
    print(f"  Word count: {TextUtils.word_count(text)}")
    print(f"  Contains Arabic: {TextUtils.contains_arabic(text)}")
    print(f"  Similarity: {TextUtils.similarity(text, 'مرحبا في AHS'):.2f}")

    # Data
    data = {"a": {"b": {"c": 42}}}
    print(f"  Safe get: {DataUtils.safe_get(data, 'a', 'b', 'c')}")

    # Time
    print(f"  Duration: {TimeUtils.format_duration(3661)}")
    print(f"  Size: {TimeUtils.human_readable_size(1048576)}")

    # Stats
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print(f"  Mean: {StatsUtils.mean(values)}")
    print(f"  Median: {StatsUtils.median(values)}")
    print(f"  StdDev: {StatsUtils.std_dev(values):.2f}")

    print("\n✅ All utilities ready")
