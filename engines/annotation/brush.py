"""画笔工具 - 自由绘制"""
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, Qt

from .base import BaseTool
from models.annotation import ToolType


class BrushTool(BaseTool):
    """画笔工具 - 自由绘制线条"""

    def __init__(self):
        super().__init__(ToolType.BRUSH)
        self._path = QPainterPath()
        self._last_point = None

    def onMousePress(self, pos: QPoint):
        self.points.append((pos.x(), pos.y()))
        self._path.moveTo(pos)
        self._last_point = pos
        self.is_active = True

    def onMouseMove(self, pos: QPoint):
        if not self.is_active:
            return
        self.points.append((pos.x(), pos.y()))
        self._path.lineTo(pos)
        self._last_point = pos

    def onMouseRelease(self, pos: QPoint):
        if not self.is_active:
            return
        self.points.append((pos.x(), pos.y()))
        if self._last_point:
            self._path.lineTo(pos)
        self.finishAnnotation()
        self._path = QPainterPath()
        self._last_point = None
        self.is_active = False

    def drawPreview(self, painter: QPainter):
        if not self.is_active or self._path.isEmpty():
            return

        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(self.color))
        pen.setWidth(self.width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(self._path)
