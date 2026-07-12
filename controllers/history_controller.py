"""历史记录控制器 - 主窗口历史面板的 QML 桥接层"""
import json
import tempfile
from PySide6.QtCore import QObject, Signal, Slot

from core.history_manager import HistoryManager
from utils.logger import logger


class HistoryController(QObject):
    """历史记录控制器 — 暴露给主窗口 QML"""

    # 信号: 用户选择了一条历史记录 (image_path, width, height)
    historyItemSelected = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = HistoryManager.instance()

    @Slot(result=str)
    def getRecentHistory(self) -> str:
        """获取最近历史记录 (JSON)"""
        try:
            items = self._history.getHistory()
            result = []
            for item in items[:20]:
                result.append({
                    "id": item.id,
                    "timestamp": item.timestamp,
                    "thumbnail_path": item.thumbnail_path,
                    "image_path": item.image_path,
                    "annotations_count": item.annotations_count,
                    "capture_mode": item.capture_mode,
                })
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error("[HistoryController] 获取历史失败: %s", e)
            return "[]"

    @Slot(str)
    def deleteHistoryItem(self, item_id: str):
        """删除历史记录项"""
        self._history.deleteRecord(item_id)
        logger.info("[HistoryController] 删除历史: %s", item_id)

    @Slot(str)
    def loadHistoryItem(self, item_id: str):
        """加载历史记录项 — 发射信号由 main.py 打开编辑器"""
        try:
            img = self._history.loadRecord(item_id)
            if img:
                # 保存到临时文件
                with tempfile.NamedTemporaryFile(suffix=".png", prefix="history_", delete=False) as tmp:
                    temp_path = tmp.name
                img.save(temp_path)
                self.historyItemSelected.emit(temp_path, img.width, img.height)
                logger.info("[HistoryController] 加载历史: %s", item_id)
        except Exception as e:
            logger.error("[HistoryController] 加载历史失败: %s", e)
