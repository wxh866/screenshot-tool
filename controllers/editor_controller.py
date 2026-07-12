"""编辑器控制器 - QML编辑器与标注引擎的桥接层

架构（参考Snipaste/ShareX/Flameshot等高星项目）：
- 非破坏性工具（线/矩形/圆/箭头/文字/画笔/高亮/多边形/智能选区）:
  作为AnnotationData存储，由QML Canvas叠加渲染 ✅
- 破坏性工具（马赛克/橡皮擦/水印）:
  立即应用到图片，更新working_image_path，QML显示新图 🎯
  每次破坏性操作前备份当前图片，支持撤销
"""
import json
import tempfile
import shutil
import time
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, Slot, Property, QPoint, QMimeData, QByteArray
from PySide6.QtGui import QGuiApplication, QPixmap, QImage
from PySide6.QtQml import QQmlApplicationEngine

from core.annotation_service import AnnotationEngine
from core.undo_manager import UndoManager
from core.history_manager import HistoryManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus, EventType
from models.annotation import AnnotationData, ToolType
from models.tool_config import DEFAULT_TOOL_CONFIGS, ToolConfig
from utils.logger import logger

# 导出器（单一导出路径，复用 engines/export/*）
from engines.export.png_exporter import PNGExporter
from engines.export.jpg_exporter import JPGExporter
from engines.export.bmp_exporter import BMPExporter
from engines.export.pdf_exporter import PDFExporter

# 破坏性工具 — 需要立即改图
_DESTRUCTIVE_TOOLS = {ToolType.MOSAIC, ToolType.ERASER, ToolType.WATERMARK,
                      ToolType.SMART_SELECT}

# 扩展名 → 导出器（单一来源，避免内联重复 save 逻辑）
_EXPORTERS = {
    ".png": PNGExporter(),
    ".jpg": JPGExporter(),
    ".jpeg": JPGExporter(),
    ".bmp": BMPExporter(),
    ".pdf": PDFExporter(),
}


class EditorController(QObject):
    """编辑器控制器"""

    canvasNeedsUpdate = Signal()
    previewUpdated = Signal(str)     # JSON: {points, tool_type, color, width}
    undoStateChanged = Signal(bool, bool)
    exportFinished = Signal(str)
    editorClosed = Signal()
    imageSourceChanged = Signal(str)  # 图片路径变化 → QML重新加载

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = AnnotationEngine()
        self._annotations: List[AnnotationData] = []
        self._current_tool = ToolType.BRUSH.value
        self._tool_color = "#FF6B35"
        self._tool_width = 7
        self._tool_opacity = 255
        self._is_drawing = False
        self._current_points: list = []
        self._working_image_path = ""    # 当前显示的图片路径（可能含破坏性修改）
        self._original_image_path = ""   # 原始截图路径（不变）
        self._annotations_json = "[]"
        self._image_backup_stack: List[str] = []  # 破坏性操作的图片备份链

        # 水印实时预览参数（拖滑块时只更新预览，不烘焙进图片）
        self._wm_preview = {
            "text": "水印", "opacity": 25, "size": 52,
            "rotation": 28, "mode": "tile",
        }

        # 工具配置
        self._tool_configs = {
            t.value: {
                "color": c.default_color, "width": c.default_width,
                "opacity": c.default_opacity, "min_width": c.min_width,
                "max_width": c.max_width,
            }
            for t, c in DEFAULT_TOOL_CONFIGS.items()
        }

        # 连接引擎信号
        self._engine.annotationAdded.connect(self._onAnnotationFinished)
        self._engine.annotationDeleted.connect(self._onAnnotationDeleted)
        self._engine.toolChanged.connect(self._onToolChanged)

        # 连接撤销管理器
        undo_mgr = UndoManager.instance()
        undo_mgr.undoStateChanged.connect(self._onUndoStateChanged)

        EventBus.instance().subscribe(EventType.ANNOTATION_ADDED, self._onBusAnnotationAdded)
        logger.info("[EditorController] 初始化完成")

    # ===== QML可调用的Slot =====

    @Slot(str)
    def selectTool(self, tool_name: str):
        try:
            tool_type = ToolType(tool_name)
            self._current_tool = tool_name
            if tool_name in self._tool_configs:
                cfg = self._tool_configs[tool_name]
                self._tool_color = cfg["color"]
                self._tool_width = cfg["width"]
                self._tool_opacity = cfg["opacity"]
            self._engine.setCurrentTool(tool_type)
            # 水印工具：进入即显示默认预览；切走则清除预览覆盖层
            if tool_name == "watermark":
                self._emitWatermarkPreview()
            else:
                self._clearWatermarkPreview()
            logger.info("[EditorController] 工具: %s", tool_name)
        except ValueError:
            logger.warning("[EditorController] 未知工具: %s", tool_name)

    @Slot(int, int)
    def mousePress(self, x: int, y: int):
        if self._current_tool == "watermark":
            return  # 水印通过按钮弹窗设置，不用鼠标拖
        self._is_drawing = True
        self._current_points = [(x, y)]
        self._engine.handleMouseEvent("Press", QPoint(x, y))
        self._updatePreview()

    @Slot(int, int)
    def mouseMove(self, x: int, y: int):
        if not self._is_drawing:
            return
        self._current_points.append((x, y))
        self._engine.handleMouseEvent("Move", QPoint(x, y))
        self._updatePreview()

    @Slot(int, int)
    def mouseRelease(self, x: int, y: int):
        if not self._is_drawing:
            return
        self._is_drawing = False
        self._current_points.append((x, y))
        self._engine.handleMouseEvent("Release", QPoint(x, y))
        self._updatePreview()
        self.previewUpdated.emit("")

    @Slot(int, int)
    def finishPolygon(self, x: int, y: int):
        """双击闭合多边形（QML polygon 工具专用）

        参考 Flameshot 多边形工具：逐点单击添加顶点，双击闭合。
        Qt 双击会先触发一次额外的 mousePress（在双击位置追加了重复顶点），
        这里先移除该重复末点，再调用工具的 onMouseDoubleClick 完成标注。
        """
        try:
            tool = self._engine.current_tool
            if tool is None or tool.tool_type != ToolType.POLYGON:
                return
            # 移除双击产生的连续重复末点（与上一个顶点相同）
            while len(tool.points) >= 2 and tool.points[-1] == tool.points[-2]:
                tool.points.pop()
            tool.onMouseDoubleClick(QPoint(x, y))
            logger.info("[EditorController] 多边形闭合: %d 个顶点", len(tool.points))
        except Exception as e:
            logger.error("[EditorController] 多边形闭合失败: %s", e)

    @Slot(str)
    def setColor(self, color: str):
        self._tool_color = color
        if self._engine.current_tool:
            self._engine.current_tool.setProperties(color, self._tool_width, self._tool_opacity)

    @Slot(int)
    def setWidth(self, width: int):
        self._tool_width = width
        if self._engine.current_tool:
            self._engine.current_tool.setProperties(self._tool_color, width, self._tool_opacity)

    @Slot(int)
    def setOpacity(self, opacity: int):
        self._tool_opacity = opacity
        if self._engine.current_tool:
            self._engine.current_tool.setProperties(self._tool_color, self._tool_width, opacity)

    @Slot(result=str)
    def getAnnotationsJson(self) -> str:
        return self._annotations_json

    @Slot(result=str)
    def getCurrentTool(self) -> str:
        return self._current_tool

    @Slot(result=str)
    def getToolColor(self) -> str:
        return self._tool_color

    @Slot(result=int)
    def getToolWidth(self) -> int:
        return self._tool_width

    @Slot(result=int)
    def getToolOpacity(self) -> int:
        return self._tool_opacity

    @Slot(result=str)
    def getToolMinWidth(self) -> str:
        if self._current_tool in self._tool_configs:
            cfg = self._tool_configs[self._current_tool]
            return json.dumps({"min": cfg["min_width"], "max": cfg["max_width"]})
        return '{"min":1,"max":30}'

    @Slot()
    def undo(self):
        """撤销 — 支持标注撤销和图片还原"""
        if self._image_backup_stack:
            # 恢复前一张备份图片
            restore_path = self._image_backup_stack.pop()
            self._working_image_path = restore_path
            # 清除当前标注（因为它们已经被破坏性操作"烘焙"进图片了）
            self._annotations.clear()
            self._updateAnnotationsJson()
            self._clearWatermarkPreview()
            self.imageSourceChanged.emit(self._working_image_path)
            logger.info("[EditorController] 撤销(图片还原)")
        else:
            # 普通标注撤销
            UndoManager.instance().undo()
            self._rebuildAnnotations()

    @Slot()
    def redo(self):
        UndoManager.instance().redo()
        self._rebuildAnnotations()

    @Slot(result=bool)
    def canUndo(self) -> bool:
        return bool(self._image_backup_stack) or UndoManager.instance().canUndo()

    @Slot(result=bool)
    def canRedo(self) -> bool:
        return UndoManager.instance().canRedo()

    @Slot()
    def clearAll(self):
        """清除所有标注"""
        self._engine.clearAll()
        self._annotations.clear()
        self._updateAnnotationsJson()
        self._clearWatermarkPreview()

    @Slot()
    def closeEditor(self):
        self.editorClosed.emit()

    @Slot(str, int, bool, bool)
    def setTextAnnotation(self, text: str, font_size: int = 20,
                          bold: bool = False, background: bool = False):
        """设置文字标注（支持多行/加粗/背景）

        参考 Flameshot/ShareX：文字作为可持久化的非破坏性标注，
        由 QML Canvas 叠加渲染，导出时由 Pillow 烘焙进图片。
        """
        try:
            if self._engine.current_tool and self._current_tool == "text":
                tool = self._engine.current_tool
                tool.properties["text"] = text
                tool.properties["font_size"] = font_size
                tool.width = font_size
                tool.setText(text, bold, background)
                logger.info("[EditorController] 文字: '%s' (字号:%d 加粗:%s 背景:%s)",
                            text, font_size, bold, background)
                return True
        except Exception as e:
            logger.error("[EditorController] 文字失败: %s", e)
        return False

    @Slot(str, int, int, int, str)
    def updateWatermarkPreview(self, text: str, opacity: int = 25, size: int = 52,
                               rotation: int = 28, mode: str = "tile"):
        """更新水印实时预览（非破坏性）

        参考 Flameshot/ShareX：拖滑块/改文字/切模式时，只把水印画在
        canvas 预览层上，不烘焙进底图，也不污染撤销栈。只有点"应用到截图"
        调用 setWatermarkParams 才真正提交。
        """
        try:
            self._wm_preview = {
                "text": text or "水印",
                "opacity": opacity,
                "size": size,
                "rotation": rotation,
                "mode": mode,
            }
            self._emitWatermarkPreview()
        except Exception as e:
            logger.error("[EditorController] 水印预览失败: %s", e)

    @Slot(str, int, int, int, str)
    def setWatermarkParams(self, text: str, opacity: int = 25, size: int = 52,
                           rotation: int = 28, mode: str = "tile"):
        """提交水印（破坏性烘焙进底图）— 仅"应用到截图"按钮调用"""
        try:
            if self._engine.current_tool and self._current_tool == "watermark":
                tool = self._engine.current_tool
                tool.setWatermarkParams(text, opacity, size, rotation, self._tool_color, mode)
                # 水印是全局破坏性工具，不需要鼠标位置，直接应用
                from models.annotation import AnnotationData
                data = AnnotationData(
                    tool_type=ToolType.WATERMARK,
                    points=[(0, 0)],
                    color=self._tool_color,
                    width=size,
                    opacity=min(opacity, 60),
                    properties=tool.properties.copy(),
                )
                self._applyDestructiveTool(data)
                # 提交后清除预览覆盖层（已烘焙进图片，避免叠加显示）
                self._wm_preview = None
                self.previewUpdated.emit("")
                logger.info("[EditorController] 水印已应用: '%s'", text)
        except Exception as e:
            logger.error("[EditorController] 水印失败: %s", e)

    def _emitWatermarkPreview(self):
        """发射水印实时预览到 canvas 覆盖层（非破坏性）"""
        if not self._wm_preview:
            return
        p = self._wm_preview
        preview = json.dumps({
            "tool_type": "watermark",
            "points": [[0, 0]],
            "color": self._tool_color,
            "width": p["size"],
            "opacity": min(p["opacity"], 60),
            "properties": {
                "text": p["text"],
                "rotation": p["rotation"],
                "mode": p["mode"],
            },
        }, ensure_ascii=False)
        self.previewUpdated.emit(preview)
        self.canvasNeedsUpdate.emit()

    def _clearWatermarkPreview(self):
        """清除水印预览覆盖层（切走工具/提交后调用）"""
        self._wm_preview = None
        self.previewUpdated.emit("")
        self.canvasNeedsUpdate.emit()

    # ===== 保存/导出 =====

    @Slot(result=str)
    def saveToFile(self) -> str:
        from PySide6.QtWidgets import QFileDialog
        if not self._working_image_path:
            return "error:no_image"

        config = ConfigManager.instance()
        default_fmt = config.get("app_config", "file_format", "PNG")
        ext_map = {"PNG": "png", "JPEG": "jpg", "BMP": "bmp", "PDF": "pdf"}
        ext = ext_map.get(default_fmt, "png")
        default_name = f"screenshot.{ext}"

        file_path, _ = QFileDialog.getSaveFileName(
            None, "保存截图", default_name,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;PDF (*.pdf)"
        )
        if not file_path:
            return "cancel"

        try:
            from PIL import Image
            base_img = Image.open(self._working_image_path)
            rendered = self._renderAnnotationsOnImage(base_img)

            # 委托给 engines/export 导出器（单一路径）
            exporter = None
            ext_lower = file_path.lower()
            for suffix, exp in _EXPORTERS.items():
                if ext_lower.endswith(suffix):
                    exporter = exp
                    break
            if exporter is None:
                exporter = PNGExporter()
            exporter.export(rendered, file_path, quality=95)

            try:
                HistoryManager.instance().addRecord(
                    rendered, self._annotations, self._current_tool
                )
            except Exception as he:
                logger.warning("[EditorController] 历史记录失败: %s", he)

            self.exportFinished.emit(file_path)
            EventBus.instance().publish(EventType.FILE_EXPORTED, file_path)
            logger.info("[EditorController] 保存: %s", file_path)
            return file_path
        except Exception as e:
            logger.error("[EditorController] 保存失败: %s", e)
            return f"error:{e}"

    @Slot(result=str)
    def copyToClipboard(self) -> str:
        try:
            from PIL import Image
            base_img = Image.open(self._working_image_path)
            rendered = self._renderAnnotationsOnImage(base_img)

            with tempfile.NamedTemporaryFile(suffix=".png", prefix="clipboard_", delete=False) as tmp:
                temp_path = tmp.name
            rendered.save(temp_path, "PNG")

            clipboard = QGuiApplication.clipboard()
            pixmap = QPixmap(temp_path)
            # 保留透明通道：Windows 上 setPixmap 只写 CF_BITMAP(24位)会丢 alpha，
            # 参考 ShareX 额外写入 image/png MIME，支持透明度的应用可拿到带 alpha 的图。
            mime = QMimeData()
            mime.setImageData(pixmap.toImage())
            with open(temp_path, "rb") as fh:
                png_bytes = fh.read()
            mime.setData("image/png", QByteArray(png_bytes))
            clipboard.setMimeData(mime)
            logger.info("[EditorController] 已复制到剪贴板")
            return "ok"
        except Exception as e:
            logger.error("[EditorController] 复制失败: %s", e)
            return f"error:{e}"

    @Slot(result=str)
    def getRecentHistory(self) -> str:
        try:
            history = HistoryManager.instance().getHistory()
            items = []
            for item in history[:20]:
                items.append({
                    "id": item.id, "timestamp": item.timestamp,
                    "thumbnail_path": item.thumbnail_path.replace("\\", "/"),
                    "image_path": item.image_path.replace("\\", "/"),
                    "annotations_count": item.annotations_count,
                    "capture_mode": item.capture_mode,
                })
            return json.dumps(items, ensure_ascii=False)
        except Exception as e:
            logger.error("[EditorController] 历史失败: %s", e)
            return "[]"

    @Slot(str)
    def loadHistoryItem(self, item_id: str):
        try:
            img = HistoryManager.instance().loadRecord(item_id)
            if img and self._working_image_path:
                img.save(self._working_image_path)
                self._annotations.clear()
                self._image_backup_stack.clear()
                self._updateAnnotationsJson()
                self.canvasNeedsUpdate.emit()
                self.imageSourceChanged.emit(self._working_image_path)
        except Exception as e:
            logger.error("[EditorController] 加载历史失败: %s", e)

    @Slot(str)
    def deleteHistoryItem(self, item_id: str):
        HistoryManager.instance().deleteRecord(item_id)

    @Slot(str)
    def setBaseImage(self, image_path: str):
        """设置底图（初始调用）"""
        self._working_image_path = image_path
        self._original_image_path = image_path
        self._annotations.clear()
        self._image_backup_stack.clear()
        logger.info("[EditorController] 底图: %s", image_path)

    # ===== 内部方法 =====

    def _onAnnotationFinished(self, data: AnnotationData):
        """标注完成回调 — 判断是破坏性还是非破坏性"""
        if data.tool_type in _DESTRUCTIVE_TOOLS:
            self._applyDestructiveTool(data)
        else:
            self._annotations.append(data)
            self._updateAnnotationsJson()
            self.canvasNeedsUpdate.emit()

    def _applyDestructiveTool(self, data: AnnotationData):
        """应用破坏性工具（马赛克/橡皮擦/水印）— 立即改图"""
        try:
            from PIL import Image

            # 1. 先把当前所有非破坏性标注渲染到图片上
            current_img = Image.open(self._working_image_path)
            rendered = self._renderAnnotationsOnImage(current_img)

            # 2. 备份当前图片（用于撤销）
            with tempfile.NamedTemporaryFile(
                suffix=".png", prefix="backup_", delete=False
            ) as tmp:
                backup_path = tmp.name
            rendered.save(backup_path, "PNG")
            self._image_backup_stack.append(backup_path)

            # 3. 应用破坏性效果
            if data.tool_type == ToolType.MOSAIC:
                rendered = self._applyMosaic(rendered, data)
            elif data.tool_type == ToolType.ERASER:
                rendered = self._applyEraser(rendered, Image.open(self._original_image_path), data)
            elif data.tool_type == ToolType.WATERMARK:
                rendered = self._applyWatermark(rendered, data)
            elif data.tool_type == ToolType.SMART_SELECT:
                rendered = self._applySmartSelect(rendered, data)

            # 4. 保存为新工作图片
            with tempfile.NamedTemporaryFile(
                suffix=".png", prefix="working_", delete=False
            ) as tmp:
                new_path = tmp.name
            rendered.save(new_path, "PNG")
            self._working_image_path = new_path

            # 5. 清除标注（它们已被烘焙进图片）
            self._annotations.clear()
            self._updateAnnotationsJson()

            # 6. 通知QML更新
            self.canvasNeedsUpdate.emit()
            self.imageSourceChanged.emit(self._working_image_path)

            logger.info("[EditorController] 破坏性工具已应用: %s", data.tool_type.value)
        except Exception as e:
            logger.error("[EditorController] 破坏性工具失败: %s", e, exc_info=True)

    def _onAnnotationDeleted(self, index: int):
        if 0 <= index < len(self._annotations):
            self._annotations.pop(index)
            self._updateAnnotationsJson()
            self.canvasNeedsUpdate.emit()

    def _onToolChanged(self, tool_name: str):
        self._current_tool = tool_name

    def _onUndoStateChanged(self, can_undo: bool, can_redo: bool):
        self.undoStateChanged.emit(
            bool(self._image_backup_stack) or can_undo,
            can_redo
        )

    def _onBusAnnotationAdded(self, data: dict):
        pass

    def _rebuildAnnotations(self):
        self._annotations = self._engine.annotations.copy()
        self._updateAnnotationsJson()
        self.canvasNeedsUpdate.emit()

    def _updateAnnotationsJson(self):
        arr = []
        for ann in self._annotations:
            arr.append({
                "tool_type": ann.tool_type.value,
                "points": ann.points,
                "color": ann.color,
                "width": ann.width,
                "opacity": ann.opacity,
                "properties": ann.properties,
            })
        self._annotations_json = json.dumps(arr, ensure_ascii=False)

    def _updatePreview(self):
        if not self._current_points:
            self.previewUpdated.emit("")
            return
        preview = json.dumps({
            "points": self._current_points,
            "tool_type": self._current_tool,
            "color": self._tool_color,
            "width": self._tool_width,
            "opacity": self._tool_opacity,
        }, ensure_ascii=False)
        self.previewUpdated.emit(preview)
        self.canvasNeedsUpdate.emit()

    # ===== Pillow渲染 =====

    def _renderAnnotationsOnImage(self, base_img):
        """在底图上渲染所有标注（非破坏性工具）"""
        from PIL import Image, ImageDraw, ImageFont
        rendered = base_img.copy().convert("RGBA")
        overlay = Image.new("RGBA", rendered.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            font = ImageFont.truetype("msyh.ttc", 20)
        except Exception:
            font = ImageFont.load_default()

        for ann in self._annotations:
            self._drawAnnotation(draw, ann, font)

        return Image.alpha_composite(rendered, overlay).convert("RGBA")

    def _applyMosaic(self, img, ann: AnnotationData):
        """像素化 — 最近邻缩放实现硬边马赛克

        参考 Flameshot / ShareX 高星项目做法：
        - 把目标区域先缩小到 1/block_size，再用最近邻放大回原尺寸，
          得到边缘清晰、不会把直线/边缘颜色稀释的像素块效果。
        - 右下角坐标为闭区间（QRect right/bottom），PIL crop 为半开区间，
          因此 +1 以包含右下角像素，避免边界漏处理导致直线"变形"。
        """
        from PIL import Image
        if len(ann.points) < 2:
            return img

        p0, p1 = ann.points[0], ann.points[-1]
        x0 = max(0, int(min(p0[0], p1[0])))
        y0 = max(0, int(min(p0[1], p1[1])))
        # points 存储为闭区间（right/bottom），PIL 用半开区间，需 +1 才能包含右下角像素
        x1 = min(img.width, int(max(p0[0], p1[0])) + 1)
        y1 = min(img.height, int(max(p0[1], p1[1])) + 1)

        if x1 <= x0 or y1 <= y0:
            return img

        block_size = ann.properties.get("block_size", 8)
        # 分离 alpha，防止后续 paste 改变原图透明度
        region = img.crop((x0, y0, x1, y1)).convert("RGBA")
        alpha = region.getchannel("A")

        # 硬边马赛克：缩小后最近邻放大
        small_w = max(1, region.width // block_size)
        small_h = max(1, region.height // block_size)
        small = region.convert("RGB").resize(
            (small_w, small_h), Image.Resampling.LANCZOS
        )
        mosaic_rgb = small.resize((region.width, region.height), Image.Resampling.NEAREST)

        mosaic = Image.merge("RGBA", (*mosaic_rgb.split(), alpha))
        result = img.copy().convert("RGBA")
        result.paste(mosaic, (x0, y0), alpha)
        return result

    def _applyEraser(self, img, base_img, ann: AnnotationData):
        """从原图恢复像素（橡皮擦）"""
        from PIL import Image
        import numpy as np
        np_img = np.array(img.convert("RGB"))
        np_base = np.array(base_img.convert("RGB"))
        h, w = np_img.shape[:2]
        radius = max(ann.width, 3)

        for pt in ann.points:
            px, py = int(pt[0]), int(pt[1])
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            np_img[ny, nx] = np_base[ny, nx]
        return Image.fromarray(np_img).convert("RGBA")

    def _applyWatermark(self, img, ann: AnnotationData):
        """在图片上渲染水印（支持旋转、平铺/居中、透明度）

        参考 Flameshot/ShareX 高星项目实现：
        - 先创建独立文字图层，按旋转角度旋转后再平铺/居中粘贴
        - 使用 alpha 通道合成，确保透明度自然
        """
        import math
        from PIL import Image, ImageDraw, ImageFont

        text = (ann.properties or {}).get("text", "水印")
        if not text:
            return img

        size = max(ann.width or 52, 8)
        rotation = (ann.properties or {}).get("rotation", 28)
        mode = (ann.properties or {}).get("mode", "tile")
        opacity = max(min(ann.opacity or 255, 255), 1)

        # 解析颜色（保留原始透明度，不强制限制为60）
        r, g, b, _ = self._hexToRGBA(ann.color, 255)
        text_color = (r, g, b, opacity)

        # 加载字体
        try:
            font = ImageFont.truetype("msyh.ttc", size)
        except Exception:
            font = ImageFont.load_default()

        # 估算文字尺寸
        tmp = Image.new("RGBA", (1, 1))
        tmp_draw = ImageDraw.Draw(tmp)
        try:
            bbox = tmp_draw.textbbox((0, 0), text, font=font)
            text_w = int(bbox[2] - bbox[0]) + 4
            text_h = int(bbox[3] - bbox[1]) + 4
        except Exception:
            text_w = size * len(text)
            text_h = size

        # 创建足够大的透明图层来绘制并旋转文字
        diag = int(math.sqrt(text_w * text_w + text_h * text_h)) + 20
        text_layer = Image.new("RGBA", (diag * 2, diag * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        draw.text((diag, diag), text, font=font, fill=text_color)

        # 旋转文字图层（Pillow rotate 逆时针，因此取负让角度与 UI 一致）
        rotated = text_layer.rotate(-rotation, resample=Image.BICUBIC, expand=False)

        # 裁剪掉透明边缘，减少平铺时的空白间距
        bbox = rotated.getbbox()
        if bbox:
            rotated = rotated.crop(bbox)

        base = img.convert("RGBA")

        if mode == "center":
            # 居中：把旋转后的文字放在图片中心
            x = (base.width - rotated.width) // 2
            y = (base.height - rotated.height) // 2
            base.paste(rotated, (x, y), rotated)
        else:
            # 平铺：错行排列，类似常见截图工具水印效果
            pad_x = max(rotated.width + size, size * 3)
            pad_y = max(rotated.height + size, size * 2)
            for row, y in enumerate(range(-rotated.height // 2, base.height + rotated.height, pad_y)):
                row_offset = (pad_x // 2) if row % 2 else 0
                for x in range(-rotated.width // 2, base.width + rotated.width, pad_x):
                    base.paste(rotated, (x + row_offset, y), rotated)

        return base

    def _applySmartSelect(self, img, ann: AnnotationData):
        """智能选区：基于 OpenCV GrabCut 自动识别前景，背景做模糊+去色处理

        参考 JamTools / OpenCV 官方 GrabCut 示例实现：
        - 以选区矩形作为"可能为前景"初始化 GrabCut
        - 迭代得到前景掩码
        - 前景保留原色，背景替换为模糊灰度（人像模式效果）
        若 OpenCV 不可用或执行失败，则回退为仅对选区外做轻微模糊。
        """
        import cv2
        import numpy as np
        from PIL import Image

        if len(ann.points) < 2:
            return img

        p0, p1 = ann.points[0], ann.points[-1]
        x0 = max(0, int(min(p0[0], p1[0])))
        y0 = max(0, int(min(p0[1], p1[1])))
        x1 = min(img.width, int(max(p0[0], p1[0])))
        y1 = min(img.height, int(max(p0[1], p1[1])))
        if x1 <= x0 or y1 <= y0:
            return img

        try:
            src = np.array(img.convert("RGB"))
            mask = np.zeros(src.shape[:2], np.uint8)
            bgd = np.zeros((1, 65), np.float64)
            fgd = np.zeros((1, 65), np.float64)
            rect = (x0, y0, x1 - x0, y1 - y0)
            cv2.grabCut(src, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
            # 前景掩码：确定前景 + 可能前景
            fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)

            base_f = src.astype(np.float32)
            # 背景：灰度 + 高斯模糊
            gray = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB).astype(np.float32)
            blur = cv2.GaussianBlur(gray3, (21, 21), 0)
            # 合成：前景保留原色，背景用模糊灰度
            out = np.where(fg[:, :, None] == 1, base_f, blur).astype(np.uint8)
            return Image.fromarray(out).convert("RGBA")
        except Exception as e:
            logger.warning("[EditorController] GrabCut 失败，回退模糊: %s", e)
            # 回退：选区外整体轻微模糊
            try:
                src = np.array(img.convert("RGB"))
                gray = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
                gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
                blur = cv2.GaussianBlur(gray3, (15, 15), 0)
                out = np.where(
                    np.fromfunction(
                        lambda yy, xx: (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1),
                        src.shape[:2], dtype=bool)[:, :, None],
                    src, blur)
                return Image.fromarray(out.astype(np.uint8)).convert("RGBA")
            except Exception:
                return img

    def _drawAnnotation(self, draw, ann: AnnotationData, font):
        """绘制单个标注（Pillow）"""
        color = self._hexToRGBA(ann.color, ann.opacity)
        points = ann.points

        if ann.tool_type == ToolType.BRUSH and len(points) >= 2:
            draw.line(points, fill=color, width=ann.width, joint="curve")
        elif ann.tool_type == ToolType.LINE and len(points) >= 2:
            draw.line([points[0], points[-1]], fill=color, width=ann.width)
        elif ann.tool_type == ToolType.RECT and len(points) >= 2:
            p0, p1 = points[0], points[-1]
            x0, y0 = min(p0[0], p1[0]), min(p0[1], p1[1])
            x1, y1 = max(p0[0], p1[0]), max(p0[1], p1[1])
            draw.rectangle([x0, y0, x1, y1], outline=color, width=ann.width)
        elif ann.tool_type == ToolType.CIRCLE and len(points) >= 2:
            p0, p1 = points[0], points[-1]
            x0, y0 = min(p0[0], p1[0]), min(p0[1], p1[1])
            x1, y1 = max(p0[0], p1[0]), max(p0[1], p1[1])
            draw.ellipse([x0, y0, x1, y1], outline=color, width=ann.width)
        elif ann.tool_type == ToolType.ARROW and len(points) >= 2:
            self._drawArrowPillow(draw, points[0], points[-1], color, ann.width)
        elif ann.tool_type == ToolType.TEXT and len(points) >= 1:
            text = ann.properties.get("text", "文字")
            text_color = ann.properties.get("text_color", ann.color)
            bold = ann.properties.get("bold", False)
            use_bg = ann.properties.get("background", False)
            try:
                text_font = ImageFont.truetype("msyh.ttc", ann.width)
            except Exception:
                text_font = font

            lines = text.split("\n")
            line_height = int(ann.width * 1.3)
            x0, y0 = points[0]

            # 背景高亮（参考 Flameshot：半透明底，保证任意底色可读）
            if use_bg:
                max_w = 0
                for ln in lines:
                    bbox = draw.textbbox((0, 0), ln, font=text_font)
                    max_w = max(max_w, bbox[2] - bbox[0])
                draw.rectangle(
                    [x0 - 4, y0 - 2, x0 + max_w + 4, y0 + len(lines) * line_height],
                    fill=(0, 0, 0, 120)
                )

            y = y0
            for ln in lines:
                draw.text((x0, y), ln, fill=text_color, font=text_font)
                y += line_height
        elif ann.tool_type == ToolType.HIGHLIGHT and len(points) >= 2:
            p0, p1 = points[0], points[-1]
            x0, y0 = min(p0[0], p1[0]), min(p0[1], p1[1])
            x1, y1 = max(p0[0], p1[0]), max(p0[1], p1[1])
            hl_color = self._hexToRGBA(ann.color, min(ann.opacity, 80))
            draw.rectangle([x0, y0, x1, y1], fill=hl_color)
        elif ann.tool_type == ToolType.SMART_SELECT and len(points) >= 2:
            p0, p1 = points[0], points[-1]
            x0, y0 = min(p0[0], p1[0]), min(p0[1], p1[1])
            x1, y1 = max(p0[0], p1[0]), max(p0[1], p1[1])
            self._drawDashedRect(draw, x0, y0, x1, y1, color, ann.width)
        elif ann.tool_type == ToolType.POLYGON:
            if len(points) >= 3:
                draw.polygon(points, outline=color, width=ann.width)
            elif len(points) == 2:
                draw.line([points[0], points[1]], fill=color, width=ann.width)

    def _drawArrowPillow(self, draw, start, end, color, width):
        """绘制箭头（Pillow 版）：主线段缩进 arrow_size，避免圆帽覆盖三角头。

        参考 Flameshot/ShareX 实现：箭头由"缩进后的线段 + 实心三角形"组成。
        """
        import math
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = max(math.sqrt(dx * dx + dy * dy), 1)
        dx /= length; dy /= length
        arrow_size = width * 5

        # 线段终点缩回到箭头底边中点，当箭头比整段还长时不画线
        if length > arrow_size:
            line_end = (
                int(end[0] - arrow_size * dx),
                int(end[1] - arrow_size * dy)
            )
            draw.line([start, line_end], fill=color, width=width)

        left = (
            int(end[0] - arrow_size * dx + arrow_size * 0.4 * dy),
            int(end[1] - arrow_size * dy - arrow_size * 0.4 * dx)
        )
        right = (
            int(end[0] - arrow_size * dx - arrow_size * 0.4 * dy),
            int(end[1] - arrow_size * dy + arrow_size * 0.4 * dx)
        )
        draw.polygon([end, left, right], fill=color)

    def _drawDashedRect(self, draw, x0, y0, x1, y1, color, width):
        dash_len = 8; gap_len = 4
        for (sx, sy, ex, ey) in [
            (x0, y0, x1, y0), (x0, y1, x1, y1),
            (x0, y0, x0, y1), (x1, y0, x1, y1)
        ]:
            if sy == ey:  # 水平
                x = sx
                while x < ex:
                    nx = min(x + dash_len, ex)
                    draw.line([(x, sy), (nx, ey)], fill=color, width=width)
                    x = nx + gap_len
            else:  # 垂直
                y = sy
                while y < ey:
                    ny = min(y + dash_len, ey)
                    draw.line([(sx, y), (ex, ny)], fill=color, width=width)
                    y = ny + gap_len

    @staticmethod
    def _hexToRGBA(hex_color: str, alpha: int = 255):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        elif len(hex_color) == 3:
            r, g, b = int(hex_color[0]*2, 16), int(hex_color[1]*2, 16), int(hex_color[2]*2, 16)
        else:
            r, g, b = 255, 0, 0
        return (r, g, b, alpha)
