"""工具数据模型"""
from dataclasses import dataclass
from typing import Dict, Any
from models.annotation import ToolType


@dataclass
class ToolConfig:
    """工具配置"""
    tool_type: ToolType
    default_color: str = "#FF3B30"
    default_width: int = 3
    default_opacity: int = 255
    min_width: int = 1
    max_width: int = 30
    shortcut: str = ""
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


# 各工具默认配置
DEFAULT_TOOL_CONFIGS = {
    ToolType.BRUSH: ToolConfig(ToolType.BRUSH, "#FF6B35", 7, 255, 1, 30),
    ToolType.LINE: ToolConfig(ToolType.LINE, "#FF3B30", 3, 255, 1, 30),
    ToolType.RECT: ToolConfig(ToolType.RECT, "#007AFF", 3, 255, 1, 30),
    ToolType.CIRCLE: ToolConfig(ToolType.CIRCLE, "#007AFF", 3, 255, 1, 30),
    ToolType.ARROW: ToolConfig(ToolType.ARROW, "#FF3B30", 3, 255, 1, 30),
    ToolType.TEXT: ToolConfig(ToolType.TEXT, "#FF3B30", 20, 255, 8, 180),
    ToolType.MOSAIC: ToolConfig(ToolType.MOSAIC, "", 8, 255, 4, 20),
    ToolType.HIGHLIGHT: ToolConfig(ToolType.HIGHLIGHT, "#FFCC02", 3, 100, 1, 30),
    ToolType.ERASER: ToolConfig(ToolType.ERASER, "", 15, 255, 5, 50),
    ToolType.WATERMARK: ToolConfig(ToolType.WATERMARK, "#888888", 52, 25, 12, 200),
    ToolType.SMART_SELECT: ToolConfig(ToolType.SMART_SELECT, "#4a8cff", 2, 255, 1, 10),
    ToolType.POLYGON: ToolConfig(ToolType.POLYGON, "#FF3B30", 2, 255, 1, 30),
}
