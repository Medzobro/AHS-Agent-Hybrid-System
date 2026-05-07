#!/usr/bin/env python3
"""
AHS - Data Exporter
====================
تصدير البيانات من النظام إلى صيغ مختلفة.

المميزات:
  - تصدير JSON, CSV, Markdown, HTML, Text
  - تحويل البيانات
  - تقارير منسقة
  - حفظ تلقائي
"""

import json, os, sys, time, csv, io
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime


class Exporter:
    """تصدير البيانات إلى صيغ مختلفة"""

    @staticmethod
    def json(data: Any, path: Optional[str] = None, pretty: bool = True) -> str:
        content = json.dumps(data, indent=2 if pretty else None,
                             ensure_ascii=False, default=str)
        if path:
            Path(path).write_text(content, encoding="utf-8")
        return content

    @staticmethod
    def csv(data: List[Dict], path: Optional[str] = None) -> str:
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        content = output.getvalue()
        if path:
            Path(path).write_text(content)
        return content

    @staticmethod
    def markdown_table(data: List[Dict], title: str = "Table",
                       path: Optional[str] = None) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = [f"# {title}", ""]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in data:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        lines.append("")
        content = "\n".join(lines)
        if path:
            Path(path).write_text(content)
        return content

    @staticmethod
    def markdown_report(data: Dict, title: str = "Report",
                        path: Optional[str] = None) -> str:
        lines = [f"# {title}", f"Generated: {datetime.now().isoformat()}", ""]
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                lines.append(f"## {key}")
                for item in value[:50]:
                    lines.append(f"- {item}")
                if len(value) > 50:
                    lines.append(f"*... and {len(value) - 50} more*")
                lines.append("")
            elif isinstance(value, dict):
                lines.append(f"## {key}")
                for k, v in value.items():
                    lines.append(f"- **{k}**: {v}")
                lines.append("")
            else:
                lines.append(f"**{key}**: {value}")
        content = "\n".join(lines)
        if path:
            Path(path).write_text(content)
        return content

    @staticmethod
    def html(data: Any, title: str = "AHS Report",
             path: Optional[str] = None) -> str:
        if isinstance(data, dict):
            body = "<dl>"
            for k, v in data.items():
                body += f"<dt>{k}</dt><dd>{v}</dd>"
            body += "</dl>"
        elif isinstance(data, list):
            body = "<table><tr>" + "".join(f"<th>{k}</th>" for k in data[0].keys()) + "</tr>"
            for row in data:
                body += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values()) + "</tr>"
            body += "</table>"
        else:
            body = f"<pre>{data}</pre>"

        content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
  body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
  th {{ background: #f0f0f0; }}
  pre {{ background: #f5f5f5; padding: 1rem; border-radius: 4px; }}
  dl dt {{ font-weight: bold; margin-top: 0.5rem; }}
</style></head>
<body><h1>{title}</h1><p>Generated: {datetime.now().isoformat()}</p>
{body}</body></html>"""
        if path:
            Path(path).write_text(content)
        return content

    @staticmethod
    def text(data: Any, path: Optional[str] = None) -> str:
        content = str(data)
        if path:
            Path(path).write_text(content)
        return content

    @staticmethod
    def detect_format(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return {
            ".json": "json", ".csv": "csv",
            ".md": "markdown", ".html": "html",
            ".txt": "text",
        }.get(ext, "text")

    @staticmethod
    def auto_export(data: Any, path: str) -> str:
        fmt = Exporter.detect_format(path)
        exporters = {
            "json": Exporter.json,
            "csv": Exporter.csv,
            "markdown": Exporter.markdown_table if isinstance(data, list) else Exporter.markdown_report,
            "html": Exporter.html,
            "text": Exporter.text,
        }
        exporter = exporters.get(fmt, Exporter.text)
        return exporter(data, path)


class ReportBuilder:
    """بناء التقارير بطريقة منظمة"""
    def __init__(self, title: str = "AHS Report"):
        self.title = title
        self.sections = []

    def add_section(self, name: str, content: Any, level: int = 1):
        self.sections.append({"name": name, "content": content, "level": level})
        return self

    def add_text(self, text: str):
        self.sections.append({"type": "text", "content": text})
        return self

    def add_table(self, headers: List[str], rows: List[List]):
        data = [dict(zip(headers, row)) for row in rows]
        self.sections.append({"type": "table", "data": data})
        return self

    def build_markdown(self) -> str:
        lines = [f"# {self.title}", f"Generated: {datetime.now().isoformat()}", ""]
        for section in self.sections:
            if "type" in section and section["type"] == "text":
                lines.append(section["content"])
                lines.append("")
            elif "type" in section and section["type"] == "table":
                data = section["data"]
                if data:
                    headers = list(data[0].keys())
                    lines.append("| " + " | ".join(headers) + " |")
                    lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for row in data:
                        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
                    lines.append("")
            else:
                prefix = "#" * section.get("level", 1)
                lines.append(f"{prefix} {section['name']}")
                lines.append(str(section["content"]))
                lines.append("")
        return "\n".join(lines)


class BatchProcessor:
    """معالجة دفعية للتصدير"""
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.processed = 0
        self.errors = 0

    def export(self, filename: str, data: Any, fmt: Optional[str] = None) -> str:
        try:
            path = self.output_dir / filename
            if fmt:
                old = path.suffix
                path = path.with_suffix(f".{fmt}")
            Exporter.auto_export(data, str(path))
            self.processed += 1
            return str(path)
        except Exception as e:
            self.errors += 1
            return f"Error: {e}"

    def export_all(self, exports: Dict[str, Any]) -> Dict[str, str]:
        results = {}
        for filename, data in exports.items():
            results[filename] = self.export(filename, data)
        return results

    def summary(self) -> str:
        return f"Exported {self.processed} files ({self.errors} errors)"


if __name__ == "__main__":
    # اختبار
    data = [
        {"name": "AHS", "version": "0.2.0", "language": "Python"},
        {"name": "OpenClaw", "version": "latest", "language": "Go"},
    ]

    print("🧪 Exporter Test")
    print(f"  JSON: {Exporter.json(data)[:60]}...")
    print(f"  CSV: {Exporter.csv(data)[:60]}...")
    print(f"  MD:  {Exporter.markdown_table(data)[:60]}...")

    report = ReportBuilder("AHS System Report")
    report.add_section("Overview", "Hybrid Agent System")
    report.add_section("Components", {"core": 3, "system": 12, "skills": 6}, level=2)
    print(f"\n📋 Report: {report.build_markdown()[:200]}...")

    processor = BatchProcessor("/tmp/ahs_test")
    results = processor.export_all({
        "test.json": data,
        "test.csv": data,
        "test.md": data,
    })
    for f, r in results.items():
        print(f"  ✅ {f} → {r}")

    print(f"\n📊 Batch: {processor.summary()}")
    print("\n✅ Exporter ready")
