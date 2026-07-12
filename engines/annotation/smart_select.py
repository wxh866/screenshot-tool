"""智能选区工具 - GrabCut算法（参考JamTools）"""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from .base import BaseTool
from models.annotation import ToolType


class SmartSelectTool(BaseTool):
    """智能选区工具 - 基于OpenCV GrabCut自动识别区域"""

    def __init__(self):
        super().__init__(ToolType.SMART_SELECT)
        self._start = None
        self._end = None
        self._has_cv = False
        self._tryImportCV()

    def _tryImportCV(self):
        """尝试导入OpenCV"""
        try:
            import cv2
            self._has_cv = True
        except ImportError:
            pass

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
        self.properties["algorithm"] = "grabcut"
        self.finishAnnotation()
        self._start = None
        self._end = None
        self.is_active = False

    def drawPreview(self, painter: QPainter):
        if not self.is_active or not self._start or not self._end:
            return

        rect = QRect(self._start, self._end).normalized()

        # 虚线矩形 + 智能选区提示
        painter.setPen(QPen(QColor("#4a8cff"), 2, Qt.DashDotLine))
        painter.drawRect(rect)

        # 提示文字
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QPainter().font())
        from PySide6.QtGui import QFont
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, "智能选区")
