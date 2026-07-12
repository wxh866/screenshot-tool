"""截图数据模型"""
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
from enum import Enum


class CaptureMode(Enum):
    """截图模式"""
    FULLSCREEN = "fullscreen"
    REGION = "region"
    WINDOW = "window"
    SCROLLING = "scrolling"


@dataclass
class ScreenshotData:
    """截图数据"""
    image_path: str = ""          # 截图文件路径
    capture_mode: CaptureMode = CaptureMode.FULLSCREEN
    width: int = 0
    height: int = 0
    timestamp: float = 0.0
    dpi_scale: float = 1.0        # DPI缩放因子
