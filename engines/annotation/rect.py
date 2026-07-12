"""矩形工具"""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QBrush

from .base import BaseTool
from models.annotation import ToolType


class RectTool(BaseTool):
    """矩形工具"""

    def __init__(self):
        super().__init__(ToolType.RECT)
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
        rect = QRect(self._start, self._end).normalized()
        # QRect(QPoint,QPoint) 为闭区间构造(width=x2-x1+1)，用 right()/bottom()
        # 取包含端点，确保存储右下角 = 光标实际位置（修复 +1 偏移）
        self.points = [
            (rect.x(), rect.y()),
            (rect.right(), rect.bottom())
        ]
        self.finishAnnotation()
        self._start = None
        self._end = None
        self.is_active = False

    def drawPreview(self, painter: QPainter):
        if not self.is_active or not self._start or not self._end:
            return

        rect = QRect(self._start, self._end).normalized()
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(self.color))
        pen.setWidth(self.width)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.NoBrush))
        painter.drawRect(rect)
