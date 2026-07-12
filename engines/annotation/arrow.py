"""箭头工具"""
import math
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF

from .base import BaseTool
from models.annotation import ToolType


class ArrowTool(BaseTool):
    """箭头工具"""

    def __init__(self):
        super().__init__(ToolType.ARROW)
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

        # 参考 Flameshot/ShareX：线段终点缩进 arrow_len，让 round cap 不突出三角头
        arrow_len = max(15, self.width * 5)
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length > arrow_len:
            line_end = QPoint(
                int(self._end.x() - arrow_len * dx / length),
                int(self._end.y() - arrow_len * dy / length)
            )
            painter.drawLine(self._start, line_end)
        # 若长度不足 arrow_len 则只画头

        # 绘制箭头头部
        self._drawArrowHead(painter, self._start, self._end)

    def _drawArrowHead(self, painter: QPainter, start: QPoint, end: QPoint):
        """绘制箭头三角头"""
        angle = math.pi / 6  # 箭头角度30度
        arrow_len = max(15, self.width * 5)

        # 计算方向角
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length < 1:
            return

        direction = math.atan2(dy, dx)

        # 箭头两侧点
        p1 = QPoint(
            int(end.x() - arrow_len * math.cos(direction - angle)),
            int(end.y() - arrow_len * math.sin(direction - angle))
        )
        p2 = QPoint(
            int(end.x() - arrow_len * math.cos(direction + angle)),
            int(end.y() - arrow_len * math.sin(direction + angle))
        )

        # 绘制三角形
        polygon = QPolygonF([end, p1, p2])
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)
