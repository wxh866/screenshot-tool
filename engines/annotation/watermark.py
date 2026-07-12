"""水印工具"""
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QColor, QFont, Qt

from .base import BaseTool
from models.annotation import ToolType


class WatermarkTool(BaseTool):
    """水印工具 - 平铺/居中两种模式"""

    def __init__(self):
        super().__init__(ToolType.WATERMARK)
        self._position = None

    def onMousePress(self, pos: QPoint):
        self._position = pos
        # 水印工具需要弹出参数对话框（由编辑器负责）

    def onMouseMove(self, pos: QPoint):
        pass

    def onMouseRelease(self, pos: QPoint):
        pass

    def setWatermarkParams(self, text: str, opacity: int = 25,
                           size: int = 52, rotation: int = 28,
                           color: str = "#888888",
                           mode: str = "tile"):
        """设置水印参数"""
        self.properties = {
            "text": text,
            "opacity": opacity,
            "size": size,
            "rotation": rotation,
            "color": color,
            "mode": mode  # tile=平铺, center=居中
        }
        if self._position:
            self.points = [(self._position.x(), self._position.y())]
            self.finishAnnotation()

    def drawPreview(self, painter: QPainter):
        if not self._position:
            return
        # 绘制光标指示
        painter.setPen(QColor(self.color))
        painter.drawLine(
            self._position,
            QPoint(self._position.x() + 20, self._position.y())
        )
