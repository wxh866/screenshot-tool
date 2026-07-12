"""撤销管理器 - Command设计模式（参考pypeek）"""
from abc import ABC, abstractmethod
from typing import List
from PySide6.QtCore import QObject, Signal

from core.event_bus import EventBus, EventType


class Command(ABC):
    """命令基类 - 所有可撤销操作都继承此类"""

    @abstractmethod
    def execute(self):
        """执行命令"""
        pass

    @abstractmethod
    def undo(self):
        """撤销命令"""
        pass

    def redo(self):
        """重做命令（默认等于再次执行）"""
        self.execute()


class AddAnnotationCommand(Command):
    """添加标注命令"""

    def __init__(self, annotation, engine):
        self.annotation = annotation
        self.engine = engine
        self.index = None

    def execute(self):
        self.engine.annotations.append(self.annotation)
        self.index = len(self.engine.annotations) - 1

    def undo(self):
        if self.index is not None and self.index < len(self.engine.annotations):
            self.engine.annotations.pop(self.index)


class DeleteAnnotationCommand(Command):
    """删除标注命令"""

    def __init__(self, index, annotation, engine):
        self.index = index
        self.annotation = annotation
        self.engine = engine

    def execute(self):
        if self.index < len(self.engine.annotations):
            self.engine.annotations.pop(self.index)

    def undo(self):
        self.engine.annotations.insert(self.index, self.annotation)


class ClearAllCommand(Command):
    """清除所有标注命令"""

    def __init__(self, engine):
        self.engine = engine
        self.saved_annotations = []

    def execute(self):
        self.saved_annotations = self.engine.annotations.copy()
        self.engine.annotations.clear()

    def undo(self):
        self.engine.annotations = self.saved_annotations.copy()


class CompositeCommand(Command):
    """组合命令 - 批量操作"""

    def __init__(self, commands: List[Command]):
        self.commands = commands

    def execute(self):
        for command in self.commands:
            command.execute()

    def undo(self):
        for command in reversed(self.commands):
            command.undo()


class UndoManager(QObject):
    """撤销管理器单例"""

    _instance = None

    # 信号：撤销状态变化（canUndo, canRedo）
    undoStateChanged = Signal(bool, bool)

    # 最大撤销步数
    MAX_UNDO_STEPS = 50

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self._initialized = True

    def execute(self, command: Command):
        """执行命令并加入撤销栈"""
        command.execute()
        self.undo_stack.append(command)
        self.redo_stack.clear()

        # 限制栈大小
        if len(self.undo_stack) > self.MAX_UNDO_STEPS:
            self.undo_stack.pop(0)

        self._notifyStateChanged()
        EventBus.instance().publish(EventType.UNDO_PERFORMED, None)

    def undo(self):
        """撤销最近操作"""
        if not self.undo_stack:
            return

        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)

        self._notifyStateChanged()
        EventBus.instance().publish(EventType.UNDO_PERFORMED, None)

    def redo(self):
        """重做最近撤销"""
        if not self.redo_stack:
            return

        command = self.redo_stack.pop()
        command.redo()
        self.undo_stack.append(command)

        self._notifyStateChanged()
        EventBus.instance().publish(EventType.REDO_PERFORMED, None)

    def canUndo(self) -> bool:
        return len(self.undo_stack) > 0

    def canRedo(self) -> bool:
        return len(self.redo_stack) > 0

    def clear(self):
        """清空所有历史"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._notifyStateChanged()

    def _notifyStateChanged(self):
        """通知撤销状态变化"""
        self.undoStateChanged.emit(self.canUndo(), self.canRedo())
        EventBus.instance().publish(EventType.UNDO_STATE_CHANGED, {
            "can_undo": self.canUndo(),
            "can_redo": self.canRedo()
        })

    @staticmethod
    def instance():
        if UndoManager._instance is None:
            UndoManager._instance = UndoManager()
        return UndoManager._instance
