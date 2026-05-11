#!/usr/bin/env python3
"""
AHS v1 — Self-Learning & Continuous Improvement System
========================================================
النظام الذي يجعل AHS يتعلم من أخطائه ويطور نفسه باستمرار.

الميزات:
  1. ErrorLogger — تسجيل كل خطأ مع stack trace كامل
  2. ErrorAnalyzer — تحليل الأنماط: هل هو خطأ متكرر؟ جديد؟ مزمن؟
  3. FixSuggestor — اقتراح إصلاحات (أو تطبيقها فوراً)
  4. CodeImprover — إعادة بناء وتحسين أي ملف
  5. PerformanceTracker — تتبع سرعة الاستجابة وتحسينها
  6. PatternLearner — تعلم من الماضي: "لما حدث خطأ X، الحل كان Y"

التعليمات:
  - يشتغل في الخلفية، لا يوقف النظام
  - عندما يجد مشكلة معروفة → يطبق الإصلاح تلقائياً
  - عندما يجد مشكلة جديدة → يسجلها ويقترح حل
"""

import ast
import hashlib
import json
import logging
import os
import re
import sqlite3
import time

logger = logging.getLogger("ahs.selflearn")

# ─── المسارات ─────────────────────────────────────────────

AHS_ROOT = os.environ.get("AHS_ROOT", 
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# قاعدة بيانات التعلم — منفصلة عن الذاكرة العادية
LEARN_DB = os.environ.get("AHS_LEARN_DB",
    os.path.join(AHS_ROOT, "data", "ahs_learn.db"))


# ═══════════════════════════════════════════════════════════════
# 1. ERROR LOGGER & ANALYZER
# ═══════════════════════════════════════════════════════════════

class ErrorEntry:
    """سجل خطأ واحد مع التحليل"""
    
    def __init__(self, 
                 error_type: str,
                 message: str,
                 file_path: str,
                 line_no: int,
                 code_snippet: str,
                 stack_trace: str,
                 context: dict | None = None):
        self.id = hashlib.md5(f"{error_type}:{file_path}:{line_no}".encode()).hexdigest()[:12]
        self.error_type = error_type
        self.message = message[:500]
        self.file_path = file_path
        self.line_no = line_no
        self.code_snippet = code_snippet[:2000]
        self.stack_trace = stack_trace[:2000]
        self.context = context or {}
        self.timestamp = time.time()
        self.severity = self._classify_severity()
    
    def _classify_severity(self) -> str:
        """HIGH / MEDIUM / LOW حسب نوع الخطأ"""
        high = ["SyntaxError", "ImportError", "ModuleNotFoundError", "Fatal", 
                "KeyboardInterrupt", "MemoryError", "SystemExit"]
        medium = ["TypeError", "KeyError", "IndexError", "ValueError", "AttributeError",
                  "ConnectionRefused", "Timeout", "BrokenPipe"]
        
        if any(h in self.error_type for h in high):
            return "HIGH"
        if any(m in self.error_type for m in medium):
            return "MEDIUM"
        return "LOW"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.error_type,
            "message": self.message,
            "file": self.file_path,
            "line": self.line_no,
            "severity": self.severity,
            "count": self.count if hasattr(self, 'count') else 1,
            "first_seen": self.timestamp,
        }


class ErrorAnalyzer:
    """
    يحلل كل خطأ جديد مقابل قاعدة البيانات لمعرفة:
    - هل هو خطأ جديد أم متكرر؟
    - كم مرة تكرر؟
    - هل يوجد حل معروف له؟
    - هل يزداد سوءاً مع الوقت؟
    """
    
    def __init__(self, db_path: str = LEARN_DB):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id TEXT PRIMARY KEY,
                    error_type TEXT NOT NULL,
                    message TEXT,
                    file_path TEXT,
                    line_no INTEGER,
                    code_snippet TEXT,
                    stack_trace TEXT,
                    severity TEXT DEFAULT 'MEDIUM',
                    category TEXT DEFAULT 'unknown',
                    count INTEGER DEFAULT 1,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    fixed BOOLEAN DEFAULT 0,
                    fix_method TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fixes (
                    id TEXT PRIMARY KEY,
                    error_id TEXT NOT NULL,
                    fix_type TEXT NOT NULL,
                    description TEXT,
                    patch TEXT,
                    applied BOOLEAN DEFAULT 0,
                    success BOOLEAN,
                    created_at REAL NOT NULL,
                    applied_at REAL,
                    FOREIGN KEY(error_id) REFERENCES errors(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    success BOOLEAN DEFAULT 1,
                    file_path TEXT,
                    context TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_type ON errors(error_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_file ON errors(file_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_perf_op ON performance(operation)
            """)
            conn.commit()
    
    def log_error(self, entry: ErrorEntry) -> dict:
        """تسجيل خطأ — إذا كان مكرراً، يزيد العداد"""
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id, count, fix_method FROM errors WHERE id = ?", 
                (entry.id,)
            ).fetchone()
            
            if existing:
                # موجود مسبقاً — يزيد العداد ويحدث الوقت
                conn.execute(
                    "UPDATE errors SET count = count + 1, last_seen = ? WHERE id = ?",
                    (time.time(), existing[0])
                )
                result = {
                    "action": "incremented",
                    "id": existing[0],
                    "total_count": existing[1] + 1,
                    "known_fix": bool(existing[2]),
                    "fix_method": existing[2],
                }
            else:
                # جديد — يُدرج
                conn.execute("""
                    INSERT INTO errors 
                    (id, error_type, message, file_path, line_no, code_snippet, 
                     stack_trace, severity, count, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    entry.id, entry.error_type, entry.message,
                    entry.file_path, entry.line_no, entry.code_snippet,
                    entry.stack_trace, entry.severity,
                    entry.timestamp, entry.timestamp
                ))
                result = {"action": "new", "id": entry.id}
            
            conn.commit()
        
        # بعد التسجيل — هل يوجد حل معروف؟
        fix = self._check_known_fix(entry)
        result["known_fix"] = fix is not None
        result["suggested_fix"] = fix
        
        return result
    
    def _check_known_fix(self, entry: ErrorEntry) -> str | None:
        """بحث في قاعدة البيانات عن حل معروف لنفس نوع الخطأ"""
        with sqlite3.connect(self.db_path) as conn:
            # هل هناك خطأ مشابه في نفس الملف؟
            similar = conn.execute("""
                SELECT e.fix_method, e.count
                FROM errors e
                WHERE e.error_type = ? 
                  AND e.file_path = ?
                  AND e.fix_method IS NOT NULL
                  AND e.fixed = 1
                ORDER BY e.count DESC
                LIMIT 1
            """, (entry.error_type, entry.file_path)).fetchone()
            
            if similar:
                return similar[0]
            
            # هل هناك خطأ مشابه في أي ملف؟
            similar_global = conn.execute("""
                SELECT e.fix_method, e.file_path
                FROM errors e
                WHERE e.error_type = ?
                  AND e.fix_method IS NOT NULL
                  AND e.fixed = 1
                ORDER BY e.count DESC
                LIMIT 1
            """, (entry.error_type,)).fetchone()
            
            if similar_global:
                return f"{similar_global[0]} (learned from {similar_global[1]})"
            
        return None
    
    def mark_fixed(self, error_id: str, fix_method: str, success: bool = True):
        """تحديد أن خطأ معين قد أصلح"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE errors SET fixed = 1, fix_method = ? WHERE id = ?",
                (fix_method, error_id)
            )
            conn.commit()
    
    def save_fix(self, error_id: str, fix_type: str, description: str, 
                 patch: str, applied: bool = False) -> str:
        """حفظ إصلاح لاستخدامه في المستقبل"""
        fix_id = hashlib.md5(f"fix:{error_id}:{time.time()}".encode()).hexdigest()[:12]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO fixes (id, error_id, fix_type, description, patch, applied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fix_id, error_id, fix_type, description, patch, applied, time.time()))
            conn.commit()
        return fix_id
    
    # ─── Performance Tracking ───────────────────────────
    
    def log_performance(self, operation: str, duration_ms: float, 
                        success: bool = True, file_path: str | None = None,
                        context: str | None = None):
        """تسجيل أداء عملية معينة"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO performance (operation, duration_ms, timestamp, success, file_path, context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (operation, duration_ms, time.time(), success, file_path, context))
            conn.commit()
    
    def get_slowest_operations(self, limit: int = 10) -> list[dict]:
        """الحصول على أبطأ العمليات"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT operation, AVG(duration_ms) as avg_duration, 
                       COUNT(*) as calls, SUM(CASE WHEN success THEN 0 ELSE 1 END) as failures
                FROM performance
                WHERE timestamp > ?
                GROUP BY operation
                ORDER BY avg_duration DESC
                LIMIT ?
            """, (time.time() - 86400, limit)).fetchall()
            
            return [
                {
                    "operation": r[0],
                    "avg_duration_ms": round(r[1], 2),
                    "calls": r[2],
                    "failures": r[3],
                    "suggestion": self._suggest_optimization(r[0], r[1]),
                }
                for r in rows
            ]
    
    def _suggest_optimization(self, operation: str, avg_ms: float) -> str | None:
        """اقتراح تحسينات للعمليات البطيئة"""
        if avg_ms > 10000:  # >10s
            return "CRITICAL: تحتاج إلى تحسين فوري"
        if avg_ms > 5000:   # >5s
            return f"HIGH: زمن الاستجابة {avg_ms/1000:.1f}s، استخدم parallel processing"
        if avg_ms > 2000:   # >2s
            return f"MEDIUM: {avg_ms/1000:.1f}s، استخدم caching"
        return None
    
    def get_frequent_errors(self, limit: int = 10) -> list[dict]:
        """الأخطاء الأكثر تكراراً"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT error_type, message, file_path, severity, count, 
                       first_seen, last_seen, fixed, fix_method
                FROM errors
                WHERE count > 1
                ORDER BY count DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [
                {
                    "type": r[0],
                    "message": r[1][:100],
                    "file": r[2],
                    "severity": r[3],
                    "count": r[4],
                    "first_seen": r[5],
                    "last_seen": r[6],
                    "fixed": bool(r[7]),
                    "fix_method": r[8],
                }
                for r in rows
            ]
    
    def get_stats(self) -> dict:
        """إحصائيات عامة"""
        with sqlite3.connect(self.db_path) as conn:
            total_errors = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            total_fixed = conn.execute("SELECT COUNT(*) FROM errors WHERE fixed = 1").fetchone()[0]
            total_fixes = conn.execute("SELECT COUNT(*) FROM fixes").fetchone()[0]
            total_perf = conn.execute("SELECT COUNT(*) FROM performance").fetchone()[0]
            
            high_severity = conn.execute(
                "SELECT COUNT(*) FROM errors WHERE severity = 'HIGH' AND fixed = 0"
            ).fetchone()[0]
            
            return {
                "total_errors_logged": total_errors,
                "total_fixed": total_fixed,
                "fix_rate": round(total_fixed / total_errors * 100, 1) if total_errors else 0,
                "total_fixes_saved": total_fixes,
                "performance_records": total_perf,
                "unresolved_high_severity": high_severity,
                "db_size_kb": round(os.path.getsize(self.db_path) / 1024, 1) if os.path.exists(self.db_path) else 0,
            }


# ═══════════════════════════════════════════════════════════════
# 2. CODE IMPROVER — إصلاح وتطوير الكود تلقائياً
# ═══════════════════════════════════════════════════════════════

class CodeImprover:
    """
    يقوم بتحسين أي ملف في المشروع:
    - إصلاح الـ imports المكررة
    - إزالة الكود الميت (unused variables, functions, imports)
    - تحسين الأداء (convert for-loops, use better data structures)
    - تطبيق best practices
    """
    
    def __init__(self, root: str = AHS_ROOT):
        self.root = root
        self.analyzer = ErrorAnalyzer()
    
    def scan_for_issues(self, file_path: str) -> list[dict]:
        """فحص ملف وإرجاع كل المشاكل المكتشفة"""
        full_path = os.path.join(self.root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path):
            return [{"error": f"File not found: {full_path}"}]
        
        with open(full_path) as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return [{"error": f"Syntax error: {e}"}]
        
        issues = []
        
        # 1. Unused imports
        all_imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    all_imports[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    src = node.module or ''
                    all_imports[f"{src}.{name}" if src else name] = node.lineno
        
        # Check which imports are actually used
        source_no_imports = re.sub(r'^import\s+\S+|^from\s+\S+\s+import\s+\S+', '', source, flags=re.MULTILINE)
        for imp_name, line_no in all_imports.items():
            base_name = imp_name.split('.')[-1]
            if base_name not in source_no_imports.split('\n')[line_no] and base_name != imp_name.split('.')[0]:
                # Check if used elsewhere (simplified)
                if base_name not in source_no_imports:
                    issues.append({
                        "type": "UNUSED_IMPORT",
                        "file": file_path,
                        "line": line_no,
                        "message": f"Import '{imp_name}' غير مستخدم",
                        "fix": f"remove line {line_no}",
                    })
        
        # 2. Bare except clauses
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "type": "BARE_EXCEPT",
                    "file": file_path,
                    "line": node.lineno,
                    "message": "Bare 'except:' يخفي كل الأخطاء — استخدم except Exception as e:",
                    "fix": "replace 'except:' with 'except Exception as e:'",
                })
        
        # 3. Very long functions (>80 lines)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno
                if func_lines > 80:
                    issues.append({
                        "type": "LONG_FUNCTION",
                        "file": file_path,
                        "line": node.lineno,
                        "message": f"دالة '{node.name}' طويلة ({func_lines} سطر)",
                        "fix": f"قسّم الدالة '{node.name}' إلى دوال أصغر",
                    })
        
        return issues
    
    def suggest_performance_improvements(self, file_path: str) -> list[dict]:
        """اقتراح تحسينات أداء"""
        full_path = os.path.join(self.root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path):
            return []
        
        with open(full_path) as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        suggestions = []
        
        for node in ast.walk(tree):
            # List comprehension instead of for-loop append
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if (isinstance(child.func, ast.Attribute) and 
                            child.func.attr == 'append' and
                            isinstance(child.func.value, ast.Name) and
                            child.func.value.id == node.target.id[:20]):
                            suggestions.append({
                                "type": "PERF_OPTIMIZATION",
                                "file": file_path,
                                "line": node.lineno,
                                "message": "حلقة for مع append — استخدم list comprehension بدلاً منها",
                                "gain": "أسرع بمرتين",
                            })
                            break
        
        return suggestions
    
    def auto_fix_imports(self, file_path: str) -> bool:
        """إزالة الـ imports غير المستخدمة تلقائياً"""
        issues = self.scan_for_issues(file_path)
        unused_imports = [i for i in issues if i["type"] == "UNUSED_IMPORT"]
        
        if not unused_imports:
            return False
        
        full_path = os.path.join(self.root, file_path) if not os.path.isabs(file_path) else file_path
        with open(full_path) as f:
            lines = f.readlines()
        
        # Remove unused import lines (from bottom to top to keep line numbers)
        lines_to_remove = sorted(set(i["line"] - 1 for i in unused_imports), reverse=True)
        for line_no in lines_to_remove:
            lines.pop(line_no)
        
        with open(full_path, 'w') as f:
            f.writelines(lines)
        
        logger.info(f"🧹 Auto-fixed {len(unused_imports)} unused imports in {file_path}")
        return True


# ═══════════════════════════════════════════════════════════════
# 3. PATTERN LEARNER — التعلم من الأخطاء للتطوير الذاتي
# ═══════════════════════════════════════════════════════════════

class PatternLearner:
    """
    يتعلم من تاريخ الأخطاء ليبني قاعدة معرفية:
    - "لما حدث خطأ في الملف X من النوع Y، الحل كان Z"
    - يتنبأ بالمشاكل المستقبلية
    - يقترح تحسينات استباقية
    """
    
    def __init__(self, analyzer: ErrorAnalyzer):
        self.analyzer = analyzer
    
    def learn_from_performance(self) -> list[dict]:
        """تعلم من أداء النظام واقتراح تحسينات"""
        slow = self.analyzer.get_slowest_operations(5)
        
        improvements = []
        for op in slow:
            if op.get("suggestion"):
                improvements.append({
                    "operation": op["operation"],
                    "current_avg_ms": op["avg_duration_ms"],
                    "suggestion": op["suggestion"],
                    "impact": "تحسين سرعة النظام",
                    "since": len(op),
                })
        
        return improvements
    
    def predict_risky_files(self) -> list[dict]:
        """تحديد الملفات التي فيها أخطاء متكررة — مرتفعة الخطورة"""
        with sqlite3.connect(self.analyzer.db_path) as conn:
            # Files with most errors
            rows = conn.execute("""
                SELECT file_path, COUNT(*) as error_count, 
                       SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                       MAX(last_seen) as latest
                FROM errors
                GROUP BY file_path
                ORDER BY error_count DESC
                LIMIT 10
            """).fetchall()
            
            return [
                {
                    "file": r[0],
                    "error_count": r[1],
                    "high_severity": r[2],
                    "risk_score": round(r[2] * 3 + r[1], 1),
                    "last_error": r[3],
                }
                for r in rows
            ]
    
    def get_system_improvements(self) -> list[dict]:
        """توليف جميع التحسينات المقترحة"""
        improvements = []
        
        # From performance
        perf_improvements = self.learn_from_performance()
        improvements.extend(perf_improvements)
        
        # From error frequency
        risky_files = self.predict_risky_files()
        for f in risky_files[:3]:
            if f["risk_score"] > 5:
                improvements.append({
                    "file": f["file"],
                    "current_errors": f["error_count"],
                    "suggestion": f"هذا الملف يحتوي على أخطاء متكررة ({f['error_count']}) — راجعه",
                    "impact": "تقليل الأخطاء",
                })
        
        # From code analysis
        improver = CodeImprover()
        for f in risky_files[:3]:
            if f["file"] and os.path.exists(os.path.join(AHS_ROOT, f["file"])):
                issues = improver.scan_for_issues(f["file"])
                for issue in issues[:2]:
                    improvements.append({
                        "file": f["file"],
                        "line": issue.get("line"),
                        "type": issue["type"],
                        "message": issue["message"],
                        "suggestion": issue.get("fix", "تحقق يدوي"),
                        "impact": "جودة الكود",
                    })
        
        return improvements


# ═══════════════════════════════════════════════════════════════
# 4. SELF-LEARNING SYSTEM — الواجهة الموحدة
# ═══════════════════════════════════════════════════════════════

class SelfLearningSystem:
    """
    النظام المركزي للتعلم الذاتي — يجمع كل المكونات.
    
    Usage:
        sls = SelfLearningSystem()
        sls.on_error(error_info)          ← يسجل ويحلل
        sls.report()                       ← تقرير كامل
        sls.suggest_improvements()         ← اقتراحات تحسين
    """
    
    def __init__(self):
        self.analyzer = ErrorAnalyzer()
        self.learner = PatternLearner(self.analyzer)
        self.improver = CodeImprover()
        self.performance_history: list[float] = []
    
    def on_startup(self):
        """عند بدء التشغيل — فحص وتحليل الماضي"""
        logger.info("🤖 Self-Learning System starting...")
        
        # Check for unresolved high-severity errors
        stats = self.analyzer.get_stats()
        if stats["unresolved_high_severity"] > 0:
            logger.warning(f"⚠️ {stats['unresolved_high_severity']} مشاكل خطيرة غير محلولة")
        
        # Get system improvement suggestions
        improvements = self.learner.get_system_improvements()
        if improvements:
            logger.info(f"💡 {len(improvements)} تحسينات مقترحة")
        
        return {
            "status": "active",
            "learn_db": self.analyzer.db_path,
            "stats": stats,
            "improvements_suggested": len(improvements),
        }
    
    def on_error(self, error: Exception, file_path: str | None = None, 
                 line_no: int | None = None, context: dict | None = None) -> dict:
        """
        معالجة خطأ — تسجيل، تحليل، اقتراح إصلاح.
        هذه الدالة تستخدم في try-except blocks في كل النظام.
        """
        error_type = type(error).__name__
        message = str(error)[:300]
        stack = traceback.format_exc()[:2000]
        
        # إنشاء إدخال الخطأ
        entry = ErrorEntry(
            error_type=error_type,
            message=message,
            file_path=file_path or "unknown",
            line_no=line_no or 0,
            code_snippet=stack[:500],
            stack_trace=stack,
            context=context
        )
        
        # تسجيل في قاعدة البيانات
        result = self.analyzer.log_error(entry)
        
        # تسجيل الأداء (فشل)
        self.analyzer.log_performance(
            f"error.{file_path or 'unknown'}", 
            duration_ms=0,
            success=False,
            file_path=file_path,
            context=message
        )
        
        # هل يوجد حل معروف؟
        if result.get("known_fix"):
            logger.info(f"💡 Fix known for {error_type}: {result['suggested_fix']}")
        
        # ما هي خطورة هذا الخطأ؟
        logger.warning(f"⚠️ [{entry.severity}] {error_type}: {message[:80]}")
        
        return result
    
    def on_success(self, operation: str, duration_ms: float, 
                   file_path: str | None = None):
        """تسجيل عملية ناجحة — لتحليل الأداء"""
        self.analyzer.log_performance(operation, duration_ms, True, file_path)
        self.performance_history.append(duration_ms)
        
        # Keep only last 1000
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]
    
    def suggest_improvements(self) -> list[dict]:
        """الحصول على كل التحسينات المقترحة حالاً"""
        return self.learner.get_system_improvements()
    
    def auto_fix_files(self) -> dict[str, bool]:
        """
        محاولة إصلاح كل الملفات تلقائياً (إزالة imports غير مستخدمة).
        يعيد dict: {file_name: was_fixed}
        """
        results = {}
        
        for root, dirs, files in os.walk(self.improver.root):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'dist', 'venv')]
            for f in files:
                if f.endswith('.py'):
                    rel_path = os.path.relpath(os.path.join(root, f), self.improver.root)
                    try:
                        fixed = self.improver.auto_fix_imports(rel_path)
                        if fixed:
                            results[rel_path] = True
                    except Exception as e:
                        logger.warning(f"⚠️ Could not fix {rel_path}: {e}")
        
        return results
    
    def report(self) -> dict:
        """تقرير كامل عن حالة التعلم الذاتي"""
        return {
            "analyzer": self.analyzer.get_stats(),
            "frequent_errors": self.analyzer.get_frequent_errors(5),
            "slowest_operations": self.analyzer.get_slowest_operations(5),
            "improvements": self.suggest_improvements()[:3],
            "recent_operations": len(self.performance_history),
        }


# ═══════════════════════════════════════════════════════════════
# Hooks — واجهات الدمج مع النظام
# ═══════════════════════════════════════════════════════════════

def wrap_with_learning(module_name: str = __name__):
    """
    لف أي دالة بـ try-except مع SelfLearningSystem.
    مثال: wrap_with_learning() ← يحمي الـ main execution.
    """
    sls = SelfLearningSystem()
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                sls.on_success(func.__name__, elapsed, func.__code__.co_filename)
                return result
            except Exception as e:
                sls.on_error(e, func.__code__.co_filename, 
                           getattr(e, 'lineno', None) or func.__code__.co_firstlineno)
                raise
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# Test & Demo
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback
    logging.basicConfig(level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print(f"\n{'='*60}")
    print("  🧪 AHS Self-Learning System — Test")
    print(f"{'='*60}\n")
    
    sls = SelfLearningSystem()
    
    # 1. Startup
    startup = sls.on_startup()
    print(f"  ✅ Startup: {startup['status']}")
    print(f"  📊 Stats: {json.dumps(startup['stats'], indent=4)}")
    
    # 2. Simulate errors
    print("\n  🧪 Simulating errors...")
    try:
        1 / 0
    except Exception as e:
        result = sls.on_error(e, "test_script.py", 10)
        print(f"  📝 Error logged: {result['action']} (id={result['id']})")
    
    try:
        {}['nonexistent']
    except Exception as e:
        result = sls.on_error(e, "test_script.py", 20)
        print(f"  📝 Error logged: {result['action']} (id={result['id']})")
    
    # Same error again (should increment counter)
    try:
        1 / 0
    except Exception as e:
        result = sls.on_error(e, "test_script.py", 10)
        print(f"  📝 Same error again: {result['action']} (total={result.get('total_count', 1)})")
    
    # 3. Performance tracking
    print("\n  📊 Simulating performance data...")
    sls.on_success("process_task", 150, "bridge/mcp_http_server.py")
    sls.on_success("process_task", 7800, "bridge/mcp_http_server.py")
    sls.on_success("web_search", 320, "system/tools.py")
    sls.on_success("process_task", 9200, "bridge/mcp_http_server.py")
    
    # 4. Report
    print("\n  📋 Self-Learning Report:")
    report = sls.report()
    print(f"     Errors logged: {report['analyzer']['total_errors_logged']}")
    print(f"     Fix rate: {report['analyzer']['fix_rate']}%")
    if report['frequent_errors']:
        print(f"     Most frequent: {report['frequent_errors'][0]['type']}")
    if report['improvements']:
        print(f"     Improvements suggested: {len(report['improvements'])}")
        for imp in report['improvements'][:2]:
            print(f"       • {imp.get('message', imp.get('suggestion', ''))[:80]}")
    
    # 5. Auto-fix
    print("\n  🧹 Auto-fixing unused imports...")
    fixed = sls.auto_fix_files()
    if fixed:
        print(f"     Fixed: {list(fixed.keys())}")
    else:
        print("     Nothing to fix (clean)")
    
    print(f"\n{'='*60}")
    print("  ✅ Self-Learning System ready for integration")
    print(f"{'='*60}")
