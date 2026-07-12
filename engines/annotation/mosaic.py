"""马赛克工具"""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from .base import BaseTool
from models.annotation import ToolType


class MosaicTool(BaseTool):
    """马赛克工具 - 像素块化"""

    def __init__(self):
        super().__init__(ToolType.MOSAIC)
        self._start = None
        self._end = None
        self.block_size = 8  # 马赛克块大小

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
        self.properties["block_size"] = self.block_size
        self.finishAnnotation()
        self._start = None
        self._end = None
        self.is_active = False

    def drawPreview(self, painter: QPainter):
        if not self.is_active or not self._start or not self._end:
            return

        rect = QRect(self._start, self._end).normalized()
        # 绘制虚线矩形预览
        painter.setPen(QPen(QColor("#4a8cff"), 1, Qt.DashLine))
        painter.drawRect(rect)

        # 绘制网格线表示马赛克效果
        painter.setPen(QPen(QColor("#ffffff"), 1, Qt.DotLine))
        x = rect.x()
        while x < rect.x() + rect.width():
            painter.drawLine(QPoint(x, rect.y()), QPoint(x, rect.y() + rect.height()))
            x += self.block_size
        y = rect.y()
        while y < rect.y() + rect.height():
            painter.drawLine(QPoint(rect.x(), y), QPoint(rect.x() + rect.width(), y))
            y += self.block_size
