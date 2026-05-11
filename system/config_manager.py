#!/usr/bin/env python3
"""
AHS - Configuration System
===========================
نظام إعدادات مركزي — يدير الإعدادات من ملف YAML/JSON وبيئة التشغيل.

Features:
  - Load config من ملف (config.yaml, config.json)
  - دعم المتغيرات البيئية
  - إعدادات افتراضية
  - تحقق من صحة الإعدادات
  - حفظ وتصدير
  - Profiles متعددة
"""

import copy
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# الإعدادات الافتراضية للنظام
DEFAULT_CONFIG = {
    "ahs": {
        "name": "AHS-Agent-Hybrid-System",
        "version": "0.2.0",
        "debug": False,
        "log_level": "INFO",
        "workspace": ".",
    },
    "model": {
        "primary": "deepseek-reasoner",
        "fallback": "deepseek-chat",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.7,
        "max_tokens": 4096,
        "thinking_mode": True,
    },
    "agent": {
        "max_workers": 3,
        "task_timeout": 120,
        "max_history": 100,
        "auto_discover_skills": True,
        "enable_memory": True,
        "enable_multi_agent": True,
    },
    "memory": {
        "max_conversations": 50,
        "max_facts": 200,
        "consolidation_interval": 3600,
        "auto_prune": True,
        "prune_threshold": 1000,
    },
    "hermes": {
        "path": os.path.expanduser("~/.local/bin/hermes"),
        "session_dir": "/data/.hermes/sessions/",
        "skills": ["dogfood"],
        "timeout": 120,
        "retry_count": 3,
    },
    "tools": {
        "enabled": True,
        "max_result_length": 5000,
        "rate_limit_per_minute": 30,
    },
    "paths": {
        "skills": "skills/",
        "generated": "generated/",
        "logs": "logs/",
        "data": "data/",
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8080,
        "enabled": False,
        "cors_origins": ["*"],
    },
}


class ConfigValidationError(Exception):
    """خطأ في Validate config"""
    pass


@dataclass
class ConfigProfile:
    """ملف تعريف إعدادات"""
    name: str
    description: str
    config: dict
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "created": self.created,
            "modified": self.modified,
        }


class ConfigManager:
    """
    مدير الإعدادات المركزي.
    يدعم:
    - إعدادات افتراضية
    - ملفات YAML/JSON
    - متغيرات بيئية
    - Profiles
    - تحقق من الصحة
    """

    def __init__(self, config_path: str | None = None):
        self.config: dict = copy.deepcopy(DEFAULT_CONFIG)
        self.profiles: dict[str, ConfigProfile] = {}
        self.current_profile: str = "default"
        self.config_file: str | None = None
        self._loaded_files: list[str] = []
        self._env_prefix = "AHS_"

        if config_path:
            self.load_file(config_path)

    def load_file(self, path: str) -> bool:
        """تحميل إعدادات من ملف JSON"""
        path_obj = Path(path)
        if not path_obj.exists():
            return False

        try:
            content = path_obj.read_text(encoding="utf-8")
            data = json.loads(content)
            self._deep_merge(self.config, data)
            self.config_file = path
            self._loaded_files.append(path)
            return True
        except (json.JSONDecodeError, Exception) as e:
            raise ConfigValidationError(f"فشل تحميل {path}: {e}")

    def load_env(self, prefix: str | None = None) -> dict:
        """تحميل إعدادات من المتغيرات البيئية"""
        prefix = prefix or self._env_prefix
        env_config = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # AHS_MODEL_PRIMARY → model.primary
                config_key = key[len(prefix):].lower().replace("_", ".")
                self._set_nested(env_config, config_key, self._parse_value(value))

        if env_config:
            self._deep_merge(self.config, env_config)

        return env_config

    def get(self, key: str, default: Any = None) -> Any:
        """الحصول على إعداد (مثال: 'model.primary' أو 'agent.max_workers')"""
        parts = key.split(".")
        current = self.config
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def set(self, key: str, value: Any):
        """تعديل إعداد"""
        parts = key.split(".")
        current = self.config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def validate(self) -> list[str]:
        """Validate config"""
        errors = []
        required_keys = ["model.provider", "model.primary"]

        for key in required_keys:
            if self.get(key) is None:
                errors.append(f"الإعداد المطلوب '{key}' غير موجود")

        # تحقق من المسارات
        paths = self.get("paths", {})
        for name, path in paths.items():
            if isinstance(path, str) and path.startswith("/"):
                p = Path(path).parent
                if not p.exists():
                    errors.append(f"المسار {path} غير موجود")

        return errors

    def save(self, path: str | None = None) -> bool:
        """Save config إلى ملف"""
        save_path = path or self.config_file or "ahs_config.json"
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def create_profile(self, name: str, description: str = "",
                       base_on_current: bool = True) -> ConfigProfile:
        """إنشاء ملف تعريف إعدادات جديد"""
        config = copy.deepcopy(self.config) if base_on_current else copy.deepcopy(DEFAULT_CONFIG)
        profile = ConfigProfile(
            name=name,
            description=description,
            config=config,
        )
        self.profiles[name] = profile
        return profile

    def switch_profile(self, name: str) -> bool:
        """التبديل إلى ملف تعريف إعدادات"""
        profile = self.profiles.get(name)
        if not profile:
            return False
        self.config = copy.deepcopy(profile.config)
        self.current_profile = name
        return True

    def reset(self):
        """إعادة تعيين الإعدادات إلى الافتراضية"""
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self._loaded_files = []

    def summary(self) -> dict:
        """Config summary"""
        return {
            "version": self.get("ahs.version"),
            "profile": self.current_profile,
            "model": self.get("model.primary"),
            "provider": self.get("model.provider"),
            "agent_max_workers": self.get("agent.max_workers"),
            "memory_enabled": self.get("agent.enable_memory"),
            "multi_agent_enabled": self.get("agent.enable_multi_agent"),
            "tools_enabled": self.get("tools.enabled"),
            "hermes_path": self.get("hermes.path"),
            "config_files_loaded": self._loaded_files,
            "profiles_count": len(self.profiles),
            "valid": len(self.validate()) == 0,
        }

    def export(self, pretty: bool = True) -> str:
        """Export config إلى JSON"""
        return json.dumps(self.config, indent=2 if pretty else None,
                         ensure_ascii=False)

    def _deep_merge(self, base: dict, overlay: dict):
        """دمج عميق بين قاموسين"""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    def _set_nested(self, d: dict, key: str, value: Any):
        """Set value في قاموس متداخل"""
        parts = key.split(".")
        current = d
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _parse_value(self, value: str) -> Any:
        """تحويل قيمة نصية إلى النوع المناسب"""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value


# ========== إعدادات سريعة لبيئات مختلفة ==========

def config_for_dev() -> ConfigManager:
    """إعدادات بيئة التطوير"""
    cfg = ConfigManager()
    cfg.set("ahs.debug", True)
    cfg.set("ahs.log_level", "DEBUG")
    cfg.set("api.enabled", False)
    cfg.create_profile("dev", "بيئة تطوير")
    return cfg


def config_for_production() -> ConfigManager:
    """إعدادات بيئة الإنتاج"""
    cfg = ConfigManager()
    cfg.set("ahs.debug", False)
    cfg.set("ahs.log_level", "WARNING")
    cfg.set("agent.max_workers", 5)
    cfg.set("api.enabled", True)
    cfg.set("api.port", 443)
    cfg.create_profile("production", "بيئة إنتاج")
    return cfg


def config_for_testing() -> ConfigManager:
    """إعدادات بيئة الاختبار"""
    cfg = ConfigManager()
    cfg.set("ahs.debug", True)
    cfg.set("agent.enable_memory", False)
    cfg.set("agent.enable_multi_agent", False)
    cfg.set("tools.rate_limit_per_minute", 100)
    cfg.create_profile("test", "بيئة اختبار")
    return cfg


# ========== أدوات مساعدة ==========

def validate_config_file(path: str) -> dict:
    """التحقق من صحة ملف إعدادات"""
    result = {"valid": False, "errors": [], "warnings": []}

    if not os.path.exists(path):
        result["errors"].append(f"الملف غير موجود: {path}")
        return result

    try:
        cfg = ConfigManager(path)
        errors = cfg.validate()
        if errors:
            result["errors"] = errors
        else:
            result["valid"] = True
        result["data"] = cfg.summary()
    except ConfigValidationError as e:
        result["errors"].append(str(e))

    return result


def generate_default_config(path: str = "ahs_config.json"):
    """توليد ملف إعدادات افتراضي"""
    cfg = ConfigManager()
    if cfg.save(path):
        return f"✅ تم إنشاء {path}"
    return f"❌ فشل إنشاء {path}"


def diff_configs(config_a: dict, config_b: dict, prefix: str = "") -> list[str]:
    """مقارنة إعدادين وإظهار الفروق"""
    differences = []
    all_keys = set(config_a.keys()) | set(config_b.keys())
    for key in all_keys:
        full_key = f"{prefix}.{key}" if prefix else key
        if key not in config_a:
            differences.append(f"+ {full_key}: {config_b[key]}")
        elif key not in config_b:
            differences.append(f"- {full_key}: {config_a[key]}")
        elif isinstance(config_a[key], dict) and isinstance(config_b[key], dict):
            differences.extend(diff_configs(config_a[key], config_b[key], full_key))
        elif config_a[key] != config_b[key]:
            differences.append(f"~ {full_key}: {config_a[key]} → {config_b[key]}")
    return differences


if __name__ == "__main__":
    print("🧪 Config Manager Test\n")

    cfg = ConfigManager()
    print(f"النموذج: {cfg.get('model.primary')}")
    print(f"المزوّد: {cfg.get('model.provider')}")
    print(f"أقصى وكلاء: {cfg.get('agent.max_workers')}")
    print(f"الذاكرة مفعلة: {cfg.get('agent.enable_memory')}")

    # تعديل
    cfg.set("agent.max_workers", 5)
    print(f"\nبعد التعديل: {cfg.get('agent.max_workers')}")

    # ملخص
    print("\n📊 الملخص:")
    for k, v in cfg.summary().items():
        print(f"  {k}: {v}")

    # Profiles
    cfg.create_profile("testing", "للاختبار")
    cfg.create_profile("production", "للإنتاج")
    print(f"\n📁 Profiles: {list(cfg.profiles.keys())}")

    # التحقق
    errors = cfg.validate()
    if errors:
        print(f"\n⚠️ أخطاء: {errors}")
    else:
        print("\n✅ الإعدادات صحيحة")
