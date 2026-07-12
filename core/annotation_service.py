"""标注引擎 - 管理12种标注工具"""
from typing import Dict, Optional, List
from PySide6.QtCore import QObject, Signal

from models.annotation import AnnotationData, ToolType
from models.tool_config import DEFAULT_TOOL_CONFIGS, ToolConfig
from engines.annotation.base import BaseTool
from core.undo_manager import UndoManager, AddAnnotationCommand
from core.event_bus import EventBus, EventType
from utils.logger import logger


class AnnotationEngine(QObject):
    """标注引擎 - 工具注册/切换/管理"""

    annotationAdded = Signal(object)     # AnnotationData
    annotationDeleted = Signal(int)      # index
    toolChanged = Signal(str)            # tool_type value

    def __init__(self):
        super().__init__()
        self.tools: Dict[ToolType, BaseTool] = {}
        self.annotations: List[AnnotationData] = []
        self.current_tool: Optional[BaseTool] = None
        self._registerTools()

    def _registerTools(self):
        """注册所有标注工具"""
        tool_map = {
            ToolType.BRUSH: "engines.annotation.brush.BrushTool",
            ToolType.LINE: "engines.annotation.line.LineTool",
            ToolType.RECT: "engines.annotation.rect.RectTool",
            ToolType.CIRCLE: "engines.annotation.circle.CircleTool",
            ToolType.ARROW: "engines.annotation.arrow.ArrowTool",
            ToolType.TEXT: "engines.annotation.text.TextTool",
            ToolType.MOSAIC: "engines.annotation.mosaic.MosaicTool",
            ToolType.HIGHLIGHT: "engines.annotation.highlight.HighlightTool",
            ToolType.ERASER: "engines.annotation.eraser.EraserTool",
            ToolType.WATERMARK: "engines.annotation.watermark.WatermarkTool",
            ToolType.SMART_SELECT: "engines.annotation.smart_select.SmartSelectTool",
            ToolType.POLYGON: "engines.annotation.polygon.PolygonTool",
        }

        for tool_type, class_path in tool_map.items():
            try:
                module_path, class_name = class_path.rsplit(".", 1)
                import importlib
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                tool = tool_class()
                self.tools[tool_type] = tool
                tool.annotationFinished.connect(self._onAnnotationFinished)
                logger.info("注册工具: %s", tool_type.value)
            except Exception as e:
                logger.warning("工具加载失败 %s: %s", tool_type.value, e)

    def setCurrentTool(self, tool_type: ToolType):
        """切换当前工具"""
        if tool_type in self.tools:
            self.current_tool = self.tools[tool_type]
            self.toolChanged.emit(tool_type.value)
            EventBus.instance().publish(EventType.TOOL_CHANGED, tool_type.value)
            logger.info("切换工具: %s", tool_type.value)
        else:
            logger.warning("工具不可用: %s", tool_type.value)

    def handleMouseEvent(self, event_type: str, pos):
        """处理鼠标事件"""
        if self.current_tool is None:
            return

        handler = getattr(self.current_tool, f"onMouse{event_type}", None)
        if handler:
            handler(pos)

    def drawPreview(self, painter):
        """绘制当前工具预览"""
        if self.current_tool:
            self.current_tool.drawPreview(painter)

    def _onAnnotationFinished(self, data: AnnotationData):
        """标注完成"""
        # 加入撤销栈（命令的execute会执行实际添加）
        command = AddAnnotationCommand(data, self)
        UndoManager.instance().execute(command)

        self.annotationAdded.emit(data)
        EventBus.instance().publish(EventType.ANNOTATION_ADDED, data.toDict())

    def deleteAnnotation(self, index: int):
        """删除标注"""
        if 0 <= index < len(self.annotations):
            annotation = self.annotations[index]
            from core.undo_manager import DeleteAnnotationCommand
            cmd = DeleteAnnotationCommand(index, annotation, self)
            UndoManager.instance().execute(cmd)
            self.annotationDeleted.emit(index)

    def clearAll(self):
        """清除所有标注"""
        from core.undo_manager import ClearAllCommand
        command = ClearAllCommand(self)
        UndoManager.instance().execute(command)

    def getAvailableTools(self) -> List[ToolType]:
        """获取可用工具列表"""
        return list(self.tools.keys())
