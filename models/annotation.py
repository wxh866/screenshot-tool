"""标注数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum


class ToolType(Enum):
    """标注工具类型"""
    BRUSH = "brush"
    LINE = "line"
    RECT = "rect"
    CIRCLE = "circle"
    ARROW = "arrow"
    TEXT = "text"
    MOSAIC = "mosaic"
    HIGHLIGHT = "highlight"
    ERASER = "eraser"
    WATERMARK = "watermark"
    SMART_SELECT = "smart_select"
    POLYGON = "polygon"


@dataclass
class AnnotationData:
    """标注数据"""
    tool_type: ToolType
    points: List[Tuple[int, int]] = field(default_factory=list)
    color: str = "#FF3B30"
    width: int = 3
    opacity: int = 255
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def toDict(self) -> Dict:
        """转为字典（用于序列化）"""
        return {
            "tool_type": self.tool_type.value,
            "points": self.points,
            "color": self.color,
            "width": self.width,
            "opacity": self.opacity,
            "properties": self.properties,
            "timestamp": self.timestamp
        }

    @staticmethod
    def fromDict(data: Dict) -> AnnotationData:
        """从字典创建"""
        return AnnotationData(
            tool_type=ToolType(data["tool_type"]),
            points=data.get("points", []),
            color=data.get("color", "#FF3B30"),
            width=data.get("width", 3),
            opacity=data.get("opacity", 255),
            properties=data.get("properties", {}),
            timestamp=data.get("timestamp", 0.0)
        )
