"""直线工具"""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from .base import BaseTool
from models.annotation import ToolType


class LineTool(BaseTool):
    """直线工具"""

    def __init__(self):
        super().__init__(ToolType.LINE)
        self._start = None
        self._end = None

    def onMousePress(self, pos: QPoint):
        self._start = pos
        self._end = pos
        self.is_active = True

    def onMouseMove(self, pos: QPoint):
        if not self.is_active:
            return
        self._end = pos

    def onMouseRelease(self, pos: QPoint):
        if not self.is_active:
            return
        self._end = pos
        self.points = [
            (self._start.x(), self._start.y()),
            (self._end.x(), self._end.y())
        ]
        self.finishAnnotation()
        self._start = None
        self._end = None
        self.is_active = False

    def drawPreview(self, painter: QPainter):
        if not self.is_active or not self._start or not self._end:
            return

        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(self.color))
        pen.setWidth(self.width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self._start, self._end)
