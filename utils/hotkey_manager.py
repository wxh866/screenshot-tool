"""快捷键管理器 — 全局热键配置 + 本地快捷键

全局热键的注册和事件处理由 NativeHotkeyFilter（main.py 中创建）负责。
本类只管理快捷键配置映射和本地 QShortcut。
"""
from typing import Callable, Dict

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QShortcut, QKeySequence

from core.config_manager import ConfigManager
from utils.logger import logger


class HotkeyManager(QObject):
    """快捷键管理器 — 配置管理 + 本地快捷键"""

    hotkeyTriggered = Signal(str)

    def __init__(self):
        super().__init__()
        self._hotkey_map: Dict[str, str] = {}
        self._local_shortcuts: Dict[str, QShortcut] = {}
        self._native_filter = None  # 由 main.py _activateGlobalHotkeys 设置
        self._loadConfig()

    def _loadConfig(self):
        """加载快捷键配置"""
        config = ConfigManager.instance()
        self._hotkey_map = config.getSection("hotkeys")
        if not self._hotkey_map:
            self._hotkey_map = {
                "capture_fullscreen": "Ctrl+Shift+F",
                "capture_region": "Ctrl+Shift+R",
                "capture_window": "Ctrl+Shift+W",
                "capture_scrolling": "Ctrl+Shift+S",
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Y",
                "save": "Ctrl+S",
                "copy": "Ctrl+C",
                "escape": "Esc",
                "delete_all": "Delete"
            }

    def registerGlobalHotkey(self, action: str):
        """注册全局热键 — 通过 NativeHotkeyFilter 调用 RegisterHotKey"""
        sequence = self._hotkey_map.get(action)
        if not sequence:
            logger.warning("[HotkeyManager] 未找到快捷键配置: %s", action)
            return

        if self._native_filter is None:
            logger.warning("[HotkeyManager] NativeHotkeyFilter 未初始化，跳过: %s", action)
            return

        self._native_filter.registerHotkey(action, sequence)

    def registerLocalShortcut(self, widget, action: str, callback: Callable):
        """注册应用内快捷键 — 仅当 widget 所在窗口激活时生效"""
        hotkey = self._hotkey_map.get(action)
        if not hotkey:
            return

        shortcut = QShortcut(QKeySequence(hotkey), widget)
        shortcut.activated.connect(callback)
        self._local_shortcuts[action] = shortcut
        logger.info("[HotkeyManager] 本地快捷键: %s → %s", action, hotkey)

    def unregisterAllGlobal(self):
        """注销所有全局热键"""
        if self._native_filter:
            self._native_filter.unregisterAll()

    def updateHotkey(self, action: str, new_hotkey: str):
        """更新快捷键绑定"""
        self._hotkey_map[action] = new_hotkey
        ConfigManager.instance().set("hotkeys", action, new_hotkey)

        if self._native_filter:
            self._native_filter.unregisterHotkey(action)
            self._native_filter.registerHotkey(action, new_hotkey)

        logger.info("[HotkeyManager] 更新快捷键: %s → %s", action, new_hotkey)
