"""橡皮擦工具"""
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QColor, QPen, Qt

from .base import BaseTool
from models.annotation import ToolType


class EraserTool(BaseTool):
    """橡皮擦工具 - 还原原图像素"""

    def __init__(self):
        super().__init__(ToolType.ERASER)
        self._last_point = None

    def onMousePress(self, pos: QPoint):
        self.points.append((pos.x(), pos.y()))
        self._last_point = pos
        self.is_active = True

    def onMouseMove(self, pos: QPoint):
        if not self.is_active:
            return
        # 两点间采样（避免快速移动漏点）
        if self._last_point:
            self._interpolatePoints(self._last_point, pos)
        self.points.append((pos.x(), pos.y()))
        self._last_point = pos

    def onMouseRelease(self, pos: QPoint):
        if not self.is_active:
            return
        self.points.append((pos.x(), pos.y()))
        self.finishAnnotation()
        self._last_point = None
        self.is_active = False

    def _interpolatePoints(self, start: QPoint, end: QPoint):
        """两点间线性插值"""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        distance = max(abs(dx), abs(dy))
        steps = max(1, distance // 3)

        for i in range(1, steps):
            x = start.x() + dx * i // steps
            y = start.y() + dy * i // steps
            self.points.append((x, y))

    def drawPreview(self, painter: QPainter):
        if not self.is_active or not self._last_point:
            return

        # 绘制橡皮擦圆形指示器
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor(255, 255, 255, 80))
        radius = self.width // 2
        painter.drawEllipse(self._last_point, radius, radius)
