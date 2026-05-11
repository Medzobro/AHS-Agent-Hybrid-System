#!/usr/bin/env python3
"""
AHS - Data Pipeline
====================
خط أنابيب البيانات — معالجة، تحويل، وتحميل.

Features:
  - Configurable pipelines
  - Middleware processors
  - Data transformation
  - Validation
  - Caching
"""

import json, os, sys, time, hashlib, threading
from typing import Dict, List, Optional, Any, Callable, Generator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PipelineStage(Enum):
    INPUT = "input"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    ENRICH = "enrich"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    OUTPUT = "output"
    CUSTOM = "custom"


@dataclass
class DataPacket:
    """Data packet flowing through the pipeline"""
    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    data: Any = None
    metadata: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stage: str = "input"
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "stage": self.stage,
            "source": self.source,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "success": self.success,
        }


class Processor:
    """Single data processor"""
    def __init__(self, name: str, handler: Callable,
                 stage: PipelineStage = PipelineStage.CUSTOM,
                 description: str = ""):
        self.name = name
        self.handler = handler
        self.stage = stage
        self.description = description
        self.call_count = 0
        self.error_count = 0
        self.total_duration = 0.0

    def process(self, packet: DataPacket) -> DataPacket:
        start = time.time()
        try:
            packet = self.handler(packet)
            self.call_count += 1
            packet.stage = self.name
        except Exception as e:
            packet.errors.append(f"{self.name}: {e}")
            self.error_count += 1
        self.total_duration += time.time() - start
        return packet


class Pipeline:
    """Complete data pipeline"""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.processors: List[Processor] = []
        self.stats = {"processed": 0, "succeeded": 0, "failed": 0}

    def add(self, handler: Callable, name: Optional[str] = None,
            stage: PipelineStage = PipelineStage.CUSTOM,
            description: str = ""):
        p = Processor(
            name=name or f"step_{len(self.processors) + 1}",
            handler=handler,
            stage=stage,
            description=description,
        )
        self.processors.append(p)
        return self

    def add_step(self, name: str, handler: Callable,
                 description: str = "") -> "Pipeline":
        return self.add(handler, name, PipelineStage.CUSTOM, description)

    def run(self, data: Any, source: str = "user",
            metadata: Optional[Dict] = None) -> DataPacket:
        packet = DataPacket(
            data=data,
            source=source,
            metadata=metadata or {},
        )

        for processor in self.processors:
            packet = processor.process(packet)
            if not packet.success:
                self.stats["failed"] += 1
                return packet

        self.stats["processed"] += 1
        self.stats["succeeded"] += 1
        return packet

    def run_batch(self, items: List) -> List[DataPacket]:
        return [self.run(item) for item in items]

    def get_stats(self) -> Dict:
        return {
            **self.stats,
            "processors": len(self.processors),
            "processor_stats": [
                {
                    "name": p.name,
                    "stage": p.stage.value,
                    "calls": p.call_count,
                    "errors": p.error_count,
                    "avg_duration": round(p.total_duration / max(p.call_count, 1), 3),
                }
                for p in self.processors
            ],
        }


class PipelineRegistry:
    """Pipeline registry"""
    def __init__(self):
        self.pipelines: Dict[str, Pipeline] = {}

    def register(self, pipeline: Pipeline) -> str:
        self.pipelines[pipeline.name] = pipeline
        return pipeline.name

    def get(self, name: str) -> Optional[Pipeline]:
        return self.pipelines.get(name)

    def list(self) -> List[Dict]:
        return [
            {"name": p.name, "description": p.description, "steps": len(p.processors)}
            for p in self.pipelines.values()
        ]

    def run(self, pipeline_name: str, data: Any) -> DataPacket:
        pipeline = self.get(pipeline_name)
        if not pipeline:
            packet = DataPacket(data=data)
            packet.errors.append(f"Pipeline '{pipeline_name}' not found")
            return packet
        return pipeline.run(data)


# ====== أمثلة: معالجات جاهزة ======

class TextProcessors:
    """Ready-made text processors"""

    @staticmethod
    def lowercase(packet: DataPacket) -> DataPacket:
        if isinstance(packet.data, str):
            packet.data = packet.data.lower()
        return packet

    @staticmethod
    def uppercase(packet: DataPacket) -> DataPacket:
        if isinstance(packet.data, str):
            packet.data = packet.data.upper()
        return packet

    @staticmethod
    def strip(packet: DataPacket) -> DataPacket:
        if isinstance(packet.data, str):
            packet.data = packet.data.strip()
        return packet

    @staticmethod
    def truncate(max_length: int = 1000):
        def _truncate(packet: DataPacket) -> DataPacket:
            if isinstance(packet.data, str) and len(packet.data) > max_length:
                packet.data = packet.data[:max_length] + "..."
                packet.warnings.append(f"Truncated to {max_length} chars")
            return packet
        return _truncate

    @staticmethod
    def remove_html(packet: DataPacket) -> DataPacket:
        import re
        if isinstance(packet.data, str):
            packet.data = re.sub(r'<[^>]+>', '', packet.data)
        return packet


class JSONProcessors:
    """Ready-made JSON processors"""

    @staticmethod
    def parse(packet: DataPacket) -> DataPacket:
        if isinstance(packet.data, str):
            try:
                packet.data = json.loads(packet.data)
            except json.JSONDecodeError as e:
                packet.errors.append(f"JSON parse error: {e}")
        return packet

    @staticmethod
    def validate(schema: Optional[Dict] = None):
        def _validate(packet: DataPacket) -> DataPacket:
            if schema and isinstance(packet.data, dict):
                for key in schema:
                    if key not in packet.data:
                        packet.warnings.append(f"Missing key: {key}")
            return packet
        return _validate

    @staticmethod
    def extract(*keys: str):
        def _extract(packet: DataPacket) -> DataPacket:
            if isinstance(packet.data, dict):
                packet.data = {k: packet.data.get(k) for k in keys}
            return packet
        return _extract


class ValidationProcessors:
    """Ready-made validation processors"""

    @staticmethod
    def not_empty(packet: DataPacket) -> DataPacket:
        if packet.data is None or (isinstance(packet.data, str) and not packet.data.strip()):
            packet.errors.append("Data is empty")
        return packet

    @staticmethod
    def max_length(n: int):
        def _check(packet: DataPacket) -> DataPacket:
            if isinstance(packet.data, str) and len(packet.data) > n:
                packet.errors.append(f"Exceeds max length {n}")
            return packet
        return _check

    @staticmethod
    def in_range(min_v: float, max_v: float):
        def _check(packet: DataPacket) -> DataPacket:
            if isinstance(packet.data, (int, float)):
                if packet.data < min_v or packet.data > max_v:
                    packet.errors.append(f"Out of range [{min_v}, {max_v}]")
            return packet
        return _check


# ====== بنائين ======

def build_text_pipeline(name: str = "text_pipeline") -> Pipeline:
    """Build basic text pipeline"""
    pipeline = Pipeline(name, "Basic text processing pipeline")
    pipeline.add(TextProcessors.strip, "strip", PipelineStage.INPUT)
    pipeline.add(TextProcessors.remove_html, "remove_html", PipelineStage.TRANSFORM)
    pipeline.add(TextProcessors.truncate(5000), "truncate", PipelineStage.TRANSFORM)
    pipeline.add(ValidationProcessors.not_empty, "validate", PipelineStage.VALIDATE)
    return pipeline


def build_json_pipeline(name: str = "json_pipeline") -> Pipeline:
    """Build basic JSON pipeline"""
    pipeline = Pipeline(name, "Basic JSON processing pipeline")
    pipeline.add(JSONProcessors.parse, "parse", PipelineStage.INPUT)
    pipeline.add(ValidationProcessors.not_empty, "validate", PipelineStage.VALIDATE)
    return pipeline


if __name__ == "__main__":
    # Example
    pipeline = build_text_pipeline()
    result = pipeline.run("  <b>Hello</b> AHS World!  " * 100)
    print(f"✅ Success: {result.success}")
    print(f"  Errors: {result.errors}")
    print(f"  Length: {len(str(result.data))} chars")
    print(f"  Pipeline stats: {pipeline.get_stats()}")

    registry = PipelineRegistry()
    registry.register(pipeline)
    print(f"\n📋 Pipelines: {len(registry.pipelines)}")
    for p in registry.list():
        print(f"  - {p['name']}: {p['steps']} steps")

    print("\n✅ Pipeline module ready")
