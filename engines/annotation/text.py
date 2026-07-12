"""文字工具

参考 Flameshot / ShareX 高星项目实现：
- 点击定位文字锚点（基线左上角）
- 支持多行文本（\n 换行）
- 支持加粗（bold）
- 支持半透明背景（background），保证在任意底色上都清晰可读
- 文字内容/字号/加粗/背景都保存在 properties 中随标注持久化
"""
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics

from .base import BaseTool
from models.annotation import ToolType


class TextTool(BaseTool):
    """文字工具 - 点击添加文字标注"""

    def __init__(self):
        super().__init__(ToolType.TEXT)
        self._position = None
        self._text = ""
        self._bold = False
        self._background = False

    def onMousePress(self, pos: QPoint):
        # 记录锚点（文字基线左上角）
        self._position = pos
        self.points = [(pos.x(), pos.y())]
        # 文字工具需要弹出输入对话框（由编辑器负责），这里仅记录位置

    def onMouseMove(self, pos: QPoint):
        # 文字工具不支持拖拽
        pass

    def onMouseRelease(self, pos: QPoint):
        pass

    def setText(self, text: str, bold: bool = False, background: bool = False):
        """设置文字内容（多行/加粗/背景），位置就绪后立即完成标注"""
        self._text = text
        self._bold = bold
        self._background = background
        self.properties["text"] = text
        self.properties["font_size"] = self.width
        self.properties["bold"] = bold
        self.properties["background"] = background
        if self._position:
            self.finishAnnotation()

    def drawPreview(self, painter: QPainter):
        # QML Canvas 负责实时预览渲染，这里仅绘制一个光标指示锚点
        if not self._position:
            return
        painter.setPen(QColor(self.color))
        painter.drawLine(
            self._position,
            QPoint(self._position.x(), self._position.y() + max(self.width, 12))
        )
