#!/usr/bin/env python3
"""
AHS - Skill Manager
====================
Skill Manager — install, enable, disable, search.

Each skill is a .py file in the skills/ folder representing a specific capability.
"""

import json, os, sys, time, uuid, importlib, inspect
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class SkillCategory(Enum):
    GENERAL = "general"           # General skills
    CODE = "code"                 # Programming
    RESEARCH = "research"         # Research
    ANALYSIS = "analysis"         # Analysis
    CREATIVE = "creative"         # Creative
    PRODUCTIVITY = "productivity" # Productivity
    SYSTEM = "system"             # System
    COMMUNICATION = "comm"       # Communication
    LEARNING = "learning"         # Learning
    CUSTOM = "custom"             # Custom


@dataclass
class Skill:
    """Loadable skill"""
    name: str
    description: str
    version: str
    category: SkillCategory
    module_path: str
    entry_point: str  # Main function name
    author: str = "AHS"
    dependencies: List[str] = field(default_factory=list)
    requires_hermes: bool = False
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    loaded: bool = False
    module: Any = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category.value,
            "author": self.author,
            "enabled": self.enabled,
            "loaded": self.loaded,
            "tags": self.tags,
            "requires_hermes": self.requires_hermes,
        }


class SkillManager:
    """
    Skill Manager — discovers, loads, runs skills.
    """

    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = skills_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "skills"
        )
        self._skills: Dict[str, Skill] = {}
        self._cache: Dict[str, Any] = {}
        self._execution_history: List[Dict] = []
        self.max_history = 500
        self.hermes_bridge = None

    def set_hermes_bridge(self, bridge):
        """Attach Hermes bridge"""
        self.hermes_bridge = bridge

    def discover(self) -> List[Skill]:
        """Discover skills in the skills/ folder"""
        skills_path = Path(self.skills_dir)
        if not skills_path.exists():
            return []

        discovered = []
        for f in skills_path.glob("*.py"):
            if f.name.startswith("_"):
                continue
            skill = self._inspect_file(f)
            if skill:
                discovered.append(skill)

        return discovered

    def _inspect_file(self, filepath: Path) -> Optional[Skill]:
        """Inspect a skill file and extract its information"""
        try:
            content = filepath.read_text(encoding="utf-8")
            module_name = filepath.stem

            # Extract description from docstring or comments
            description = ""
            for line in content.splitlines()[:20]:
                if line.strip().startswith('"""') and not description:
                    end = line.find('"""', 3)
                    if end > 0:
                        description = line[3:end]
                    break
                elif line.strip().startswith('#') and not description:
                    description = line.strip('# ')
                    break

            if not description:
                description = f"Skill {module_name}"

            # Determine category from content
            category = SkillCategory.GENERAL
            content_lower = content.lower()
            if any(w in content_lower for w in ["research", "بحث", "learn", "تعلم"]):
                category = SkillCategory.RESEARCH
            elif any(w in content_lower for w in ["code", "برمج", "python", "كود"]):
                category = SkillCategory.CODE
            elif any(w in content_lower for w in ["analyze", "تحليل", "review"]):
                category = SkillCategory.ANALYSIS
            elif any(w in content_lower for w in ["write", "create", "توليد"]):
                category = SkillCategory.CREATIVE

            return Skill(
                name=module_name,
                description=description,
                version="1.0.0",
                category=category,
                module_path=str(filepath),
                entry_point="run",
                tags=[category.value],
            )
        except Exception:
            return None

    def load_all(self) -> int:
        """Load all discovered skills"""
        discovered = self.discover()
        count = 0
        for skill in discovered:
            try:
                self._skills[skill.name] = skill
                count += 1
            except Exception as e:
                print(f"⚠️ Failed to load {skill.name}: {e}")
        return count

    def load(self, skill_name: str) -> bool:
        """Load a specific skill"""
        if skill_name in self._skills:
            skill = self._skills[skill_name]
            if skill.loaded:
                return True
            try:
                spec = importlib.util.spec_from_file_location(
                    skill.name, skill.module_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    skill.module = module
                    skill.loaded = True
                    return True
            except Exception:
                pass
        return False

    def unload(self, skill_name: str):
        """Unload a skill"""
        if skill_name in self._skills:
            self._skills[skill_name].loaded = False
            self._skills[skill_name].module = None

    def execute(self, skill_name: str, **kwargs) -> Dict:
        """Run a skill"""
        start = time.time()
        skill = self._skills.get(skill_name)

        if not skill:
            return {"success": False, "error": f"Skill '{skill_name}' not found"}
        if not skill.enabled:
            return {"success": False, "error": f"Skill '{skill_name}' is disabled"}

        # Load if not loaded
        if not skill.loaded:
            loaded = self.load(skill_name)
            if not loaded:
                # Use basic mode: send request to Hermes
                return self._execute_via_hermes(skill_name, kwargs)

        try:
            if skill.module:
                # Run the main function
                func = getattr(skill.module, skill.entry_point, None)
                if func and callable(func):
                    result = func(**kwargs)
                else:
                    # Search for any public function
                    for name, obj in inspect.getmembers(skill.module):
                        if callable(obj) and not name.startswith("_"):
                            if name == skill.entry_point or name == "run":
                                result = obj(**kwargs)
                                break
                    else:
                        result = "Skill does not contain a run function"
            else:
                result = self._execute_via_hermes(skill_name, kwargs)

            elapsed = time.time() - start
            self._log_execution(skill_name, True, elapsed)

            return {
                "success": True,
                "skill": skill_name,
                "result": str(result)[:1000],
                "elapsed": round(elapsed, 2),
            }

        except Exception as e:
            elapsed = time.time() - start
            self._log_execution(skill_name, False, elapsed, str(e))
            return {
                "success": False,
                "skill": skill_name,
                "error": f"{type(e).__name__}: {str(e)}",
                "elapsed": round(elapsed, 2),
            }

    def _execute_via_hermes(self, skill_name: str, kwargs: Dict) -> str:
        """Execute skill via Hermes"""
        if not self.hermes_bridge:
            return "Hermes bridge not available"

        task = f"Execute skill {skill_name} with parameters: {json.dumps(kwargs, ensure_ascii=False)}"
        result = self.hermes_bridge.send_task(
            task=task,
            skills=skill_name,
            thinking_mode=True,
            timeout=60
        )

        if result.get("success"):
            resp = result.get("response", {})
            return resp.get("content", "") or resp.get("content_raw", "") or "Done"
        return f"Failed: {result.get('error')}"

    def enable(self, skill_name: str) -> bool:
        """Enable a skill"""
        skill = self._skills.get(skill_name)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable(self, skill_name: str) -> bool:
        """Disable a skill"""
        skill = self._skills.get(skill_name)
        if skill:
            skill.enabled = False
            skill.loaded = False
            skill.module = None
            return True
        return False

    def get(self, skill_name: str) -> Optional[Skill]:
        """Get a skill"""
        return self._skills.get(skill_name)

    def list(self, category: Optional[SkillCategory] = None,
             enabled_only: bool = True) -> List[Skill]:
        """List skills"""
        skills = self._skills.values()
        if enabled_only:
            skills = [s for s in skills if s.enabled]
        if category:
            skills = [s for s in skills if s.category == category]
        return sorted(skills, key=lambda s: s.name)

    def search(self, query: str) -> List[Skill]:
        """Search skills"""
        query = query.lower()
        results = []
        for skill in self._skills.values():
            if (query in skill.name.lower() or
                query in skill.description.lower() or
                any(query in t.lower() for t in skill.tags)):
                results.append(skill)
        return results

    def get_stats(self) -> Dict:
        """Skill statistics"""
        total = len(self._skills)
        loaded = sum(1 for s in self._skills.values() if s.loaded)
        enabled = sum(1 for s in self._skills.values() if s.enabled)
        by_category = {}
        for s in self._skills.values():
            cat = s.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        recent = self._execution_history[-10:] if self._execution_history else []
        success_rate = 0
        if self._execution_history:
            success_rate = round(
                sum(1 for e in self._execution_history if e["success"]) /
                len(self._execution_history) * 100, 1
            )

        return {
            "total": total,
            "loaded": loaded,
            "enabled": enabled,
            "by_category": by_category,
            "total_executions": len(self._execution_history),
            "success_rate": success_rate,
            "recent_executions": recent,
        }

    def _log_execution(self, skill: str, success: bool,
                       elapsed: float, error: Optional[str] = None):
        self._execution_history.append({
            "skill": skill,
            "success": success,
            "elapsed": round(elapsed, 2),
            "error": error,
            "time": time.time(),
        })
        if len(self._execution_history) > self.max_history:
            self._execution_history = self._execution_history[-self.max_history:]

    def create_skill(self, name: str, code: str) -> bool:
        """Create a new skill file"""
        filepath = Path(self.skills_dir) / f"{name}.py"
        if filepath.exists():
            return False
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(code, encoding="utf-8")
        # Add to registry
        skill = self._inspect_file(filepath)
        if skill:
            self._skills[skill.name] = skill
        return True

    def remove_skill(self, name: str) -> bool:
        """Delete a skill"""
        skill = self._skills.get(name)
        if not skill:
            return False
        path = Path(skill.module_path)
        if path.exists():
            path.unlink()
        self._skills.pop(name, None)
        return True

    def export_manifest(self) -> str:
        """Export skill list to JSON"""
        return json.dumps(
            {n: s.to_dict() for n, s in self._skills.items()},
            indent=2, ensure_ascii=False
        )


def dump_skills_table(manager: SkillManager) -> str:
    """Display skills in a text table"""
    lines = ["# 🛠️ Available Skills", ""]
    for cat in SkillCategory:
        skills = manager.list(category=cat)
        if not skills:
            continue
        lines.append(f"## {cat.value.upper()}")
        for s in skills:
            status = "✅" if s.loaded else "⏳" if s.enabled else "❌"
            lines.append(f"- {status} **{s.name}** v{s.version}: {s.description}")
        lines.append("")
    lines.append(f"\n📊 Total: {len(manager.list())} skills")
    return "\n".join(lines)


if __name__ == "__main__":
    mgr = SkillManager()
    count = mgr.load_all()
    print(dump_skills_table(mgr))
    print(f"\n✅ Loaded {count} skills")