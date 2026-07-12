"""事件总线 - 模块间解耦通信（参考Umi-OCR架构）"""
from enum import Enum
from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal

from utils.logger import logger


class EventType(Enum):
    """事件类型定义"""
    # 截图事件
    SCREENSHOT_CAPTURED = "screenshot_captured"
    SCREENSHOT_MODE_CHANGED = "screenshot_mode_changed"

    # 标注事件
    TOOL_CHANGED = "tool_changed"
    ANNOTATION_ADDED = "annotation_added"
    ANNOTATION_DELETED = "annotation_deleted"
    ANNOTATION_MODIFIED = "annotation_modified"

    # 撤销事件
    UNDO_PERFORMED = "undo_performed"
    REDO_PERFORMED = "redo_performed"
    UNDO_STATE_CHANGED = "undo_state_changed"

    # 主题事件
    THEME_CHANGED = "theme_changed"

    # 文件事件
    FILE_EXPORTED = "file_exported"
    FILE_COPIED = "file_copied"

    # 历史事件
    HISTORY_UPDATED = "history_updated"

    # 配置事件
    CONFIG_CHANGED = "config_changed"


class EventBus(QObject):
    """事件总线单例 - 发布订阅模式"""

    _instance = None

    # Qt信号用于UI层通知
    eventPublished = Signal(str, "QVariant")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._initialized = True

    def subscribe(self, event_type: EventType, callback: Callable):
        """订阅事件"""
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """取消订阅（安全删除，不存在时静默忽略）"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass  # 回调不在列表中，安全忽略

    def publish(self, event_type: EventType, data: Any = None):
        """发布事件"""
        # 调用Python回调
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.warning("[EventBus] 回调错误: %s", e)

        # 发送Qt信号（用于QML层）
        self.eventPublished.emit(event_type.value, data)

    def clear(self):
        """清空所有订阅"""
        self._subscribers.clear()

    @staticmethod
    def instance():
        if EventBus._instance is None:
            EventBus._instance = EventBus()
        return EventBus._instance
