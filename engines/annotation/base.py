"""标注工具基类"""
import time
from abc import ABC, abstractmethod
from typing import List, Tuple
from PySide6.QtCore import QObject, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, Qt

from models.annotation import AnnotationData, ToolType
from core.undo_manager import UndoManager


class BaseTool(QObject):
    """标注工具基类 - 所有标注工具继承此类"""

    annotationFinished = Signal(object)  # AnnotationData

    def __init__(self, tool_type: ToolType):
        super().__init__()
        self.tool_type = tool_type
        self.points: List[Tuple[int, int]] = []
        self.color = "#FF3B30"
        self.width = 3
        self.opacity = 255
        self.is_active = False
        self.properties: dict = {}  # 工具专用属性

    @abstractmethod
    def onMousePress(self, pos: QPoint):
        """鼠标按下处理"""
        pass

    @abstractmethod
    def onMouseMove(self, pos: QPoint):
        """鼠标移动处理"""
        pass

    @abstractmethod
    def onMouseRelease(self, pos: QPoint):
        """鼠标释放处理"""
        pass

    @abstractmethod
    def drawPreview(self, painter: QPainter):
        """绘制预览（QPainter实时渲染）"""
        pass

    def setProperties(self, color: str, width: int, opacity: int = 255):
        """设置工具属性"""
        self.color = color
        self.width = width
        self.opacity = opacity

    def finishAnnotation(self):
        """完成标注，发送数据

        注意：必须把 self.properties 一并带上，否则依赖 properties 的工具
        （文字的 text/font_size、马赛克的 block_size、高亮的 alpha 等）
        在渲染/导出时会丢失关键参数。参考 Flameshot/ShareX 标注数据的做法：
        工具专用属性随标注一起持久化。
        """
        data = AnnotationData(
            tool_type=self.tool_type,
            points=self.points.copy(),
            color=self.color,
            width=self.width,
            opacity=self.opacity,
            properties=self.properties.copy(),
            timestamp=time.time()
        )
        self.annotationFinished.emit(data)
        self.points.clear()

    def getPen(self) -> QPen:
        """获取当前画笔"""
        pen = QPen(QColor(self.color))
        pen.setWidth(self.width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def reset(self):
        """重置工具状态"""
        self.points.clear()
        self.is_active = False
