"""历史记录管理器"""
import json
import time
import uuid
import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from PIL import Image

from PySide6.QtCore import QObject, Signal

from core.event_bus import EventBus, EventType
from core.config_manager import ConfigManager
from models.annotation import AnnotationData
from utils.logger import logger
from utils.image_utils import createThumbnail
from utils.app_dir import get_data_dir


@dataclass
class HistoryItem:
    """历史记录项"""
    id: str
    timestamp: float
    image_path: str
    thumbnail_path: str
    annotations_count: int
    capture_mode: str
    metadata: dict


class HistoryManager(QObject):
    """历史记录管理器"""

    _instance = None

    @staticmethod
    def instance():
        if HistoryManager._instance is None:
            HistoryManager._instance = HistoryManager()
        return HistoryManager._instance

    historyUpdated = Signal()

    MAX_HISTORY = 50

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self.history: List[HistoryItem] = []
        self._history_dir = self._getHistoryDir()
        self._loadHistory()
        self._initialized = True

    def _getHistoryDir(self) -> Path:
        """获取历史记录目录"""
        max_items = ConfigManager.instance().get("app_config", "max_history", 50)
        self.MAX_HISTORY = max_items
        return get_data_dir() / "history"

    def addRecord(self, image: Image.Image,
                  annotations: List[AnnotationData],
                  capture_mode: str = "fullscreen") -> HistoryItem:
        """添加历史记录"""
        self._history_dir.mkdir(parents=True, exist_ok=True)

        item_id = str(uuid.uuid4())
        timestamp = time.time()

        # 保存原图
        image_path = str(self._history_dir / f"{item_id}.png")
        image.save(image_path)

        # 生成缩略图
        thumbnail = createThumbnail(image, (200, 200))
        thumbnail_path = str(self._history_dir / f"{item_id}_thumb.png")
        thumbnail.save(thumbnail_path)

        # 创建记录
        item = HistoryItem(
            id=item_id,
            timestamp=timestamp,
            image_path=image_path,
            thumbnail_path=thumbnail_path,
            annotations_count=len(annotations),
            capture_mode=capture_mode,
            metadata={}
        )

        self.history.append(item)

        # 限制数量
        while len(self.history) > self.MAX_HISTORY:
            old_item = self.history.pop(0)
            self._deleteItemFiles(old_item)

        self._saveHistory()
        self.historyUpdated.emit()
        EventBus.instance().publish(EventType.HISTORY_UPDATED, item_id)

        logger.info("添加历史记录: %s", item_id)
        return item

    def deleteRecord(self, item_id: str):
        """删除历史记录"""
        for item in self.history:
            if item.id == item_id:
                self._deleteItemFiles(item)
                self.history.remove(item)
                break
        self._saveHistory()
        self.historyUpdated.emit()

    def getHistory(self) -> List[HistoryItem]:
        """获取历史记录列表（按时间倒序）"""
        return sorted(self.history, key=lambda x: x.timestamp, reverse=True)

    def loadRecord(self, item_id: str) -> Optional[Image.Image]:
        """加载历史记录图像（调用方负责关闭返回的Image）"""
        for item in self.history:
            if item.id == item_id and os.path.exists(item.image_path):
                return Image.open(item.image_path)
        return None

    def _deleteItemFiles(self, item: HistoryItem):
        """删除记录相关文件"""
        for path in [item.image_path, item.thumbnail_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning("删除文件失败 %s: %s", path, e)

    def _saveHistory(self):
        """保存历史记录到文件"""
        data = []
        for item in self.history:
            data.append({
                "id": item.id,
                "timestamp": item.timestamp,
                "image_path": item.image_path,
                "thumbnail_path": item.thumbnail_path,
                "annotations_count": item.annotations_count,
                "capture_mode": item.capture_mode,
                "metadata": item.metadata
            })

        history_file = self._history_dir / "history.json"
        try:
            with open(str(history_file), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存历史记录失败: %s", e)

    def _loadHistory(self):
        """从文件加载历史记录"""
        history_file = self._history_dir / "history.json"
        if not history_file.exists():
            return

        try:
            with open(str(history_file), "r", encoding="utf-8") as f:
                data = json.load(f)

            for item_data in data:
                if os.path.exists(item_data.get("image_path", "")):
                    item = HistoryItem(
                        id=item_data["id"],
                        timestamp=item_data["timestamp"],
                        image_path=item_data["image_path"],
                        thumbnail_path=item_data["thumbnail_path"],
                        annotations_count=item_data.get("annotations_count", 0),
                        capture_mode=item_data.get("capture_mode", "fullscreen"),
                        metadata=item_data.get("metadata", {})
                    )
                    self.history.append(item)

            logger.info("加载历史记录: %d条", len(self.history))

        except Exception as e:
            logger.error("加载历史记录失败: %s", e)
