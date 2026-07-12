"""多边形截图工具"""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF, QBrush

from .base import BaseTool
from models.annotation import ToolType


class PolygonTool(BaseTool):
    """多边形工具 - 逐点绘制不规则形状"""

    def __init__(self):
        super().__init__(ToolType.POLYGON)
        self._is_closed = False

    def onMousePress(self, pos: QPoint):
        if self._is_closed:
            self.reset()
            self._is_closed = False

        self.points.append((pos.x(), pos.y()))
        self.is_active = True

    def onMouseMove(self, pos: QPoint):
        # 多边形不支持拖拽，但可以显示到当前点的引导线
        pass

    def onMouseRelease(self, pos: QPoint):
        pass

    def onMouseDoubleClick(self, pos: QPoint):
        """双击闭合多边形（顶点已由单击添加，双击仅用于闭合，不再重复追加）"""
        self._is_closed = True
        self.finishAnnotation()

    def drawPreview(self, painter: QPainter):
        if not self.is_active or len(self.points) < 2:
            # 绘制起始点标记
            if self.points:
                pt = QPoint(self.points[0][0], self.points[0][1])
                painter.setPen(QPen(QColor("#4a8cff"), 2))
                painter.drawEllipse(pt, 5, 5)
            return

        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制线段
        pen = QPen(QColor(self.color))
        pen.setWidth(self.width)
        painter.setPen(pen)

        for i in range(len(self.points) - 1):
            p1 = QPoint(self.points[i][0], self.points[i][1])
            p2 = QPoint(self.points[i + 1][0], self.points[i + 1][1])
            painter.drawLine(p1, p2)

        # 闭合后填充
        if self._is_closed:
            polygon = QPolygonF()
            for pt in self.points:
                polygon.append(QPoint(pt[0], pt[1]))
            color = QColor(self.color)
            color.setAlpha(50)
            painter.setBrush(QBrush(color))
            painter.drawPolygon(polygon)

        # 绘制各顶点
        for pt in self.points:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(QPoint(pt[0], pt[1]), 3, 3)
