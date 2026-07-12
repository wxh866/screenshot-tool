"""主题管理器 - 加载/切换/查询主题"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from PySide6.QtCore import QObject, Signal, Slot

from core.event_bus import EventBus, EventType
from themes.wcag_validator import validate_theme
from utils.logger import logger


def _get_themes_dir():
    """获取主题目录（兼容开发环境和 PyInstaller onefile 模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "themes"
    return Path(__file__).parent


class ThemeManager(QObject):
    """主题管理器单例"""

    _instance = None

    # Qt信号
    themeChanged = Signal(str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._themes: Dict[str, dict] = {}
        self._current_theme: str = "dark"
        self._loadThemes()
        self._initialized = True

    def _loadThemes(self):
        """加载所有主题JSON文件"""
        theme_dir = _get_themes_dir()

        for theme_file in theme_dir.glob("*.json"):
            try:
                with open(theme_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._themes[data["name"]] = data
            except Exception as e:
                logger.warning("[ThemeManager] 加载主题失败 %s: %s", theme_file, e)

        # 验证主题
        for name, data in self._themes.items():
            issues = validate_theme(data)
            if issues:
                logger.warning("[ThemeManager] 主题 '%s' 存在 %d 个问题:", name, len(issues))
                for issue in issues:
                    logger.warning("  - %s", issue)

    @Slot(str)
    def switchTheme(self, theme_name: str):
        """切换主题"""
        if theme_name in self._themes:
            self._current_theme = theme_name
            self.themeChanged.emit(theme_name)
            EventBus.instance().publish(EventType.THEME_CHANGED, theme_name)

    @Slot(result=str)
    def toggleTheme(self) -> str:
        """切换到另一主题"""
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.switchTheme(new_theme)
        return new_theme

    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def getTheme(self, theme_name: str = None) -> dict:
        """获取主题数据"""
        name = theme_name or self._current_theme
        return self._themes.get(name, {})

    def getColor(self, color_key: str, theme_name: str = None) -> str:
        """获取主题颜色

        支持点分路径: "background.card", "text.primary", "accent.primary"
        """
        theme = self.getTheme(theme_name)
        keys = color_key.split('.')
        result = theme
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result

    def getAnnotationColors(self, theme_name: str = None) -> List[str]:
        """获取标注色板（所有主题共用）"""
        theme = self.getTheme(theme_name)
        return theme.get("annotation_colors", [])

    def getWatermarkPalette(self, theme_name: str = None) -> List[str]:
        """获取水印色板"""
        theme = self.getTheme(theme_name)
        return theme.get("watermark_palette", [])

    @Slot(result=bool)
    def isDark(self) -> bool:
        """当前是否深色主题"""
        return self._current_theme == "dark"

    @Slot(result=str)
    def getCurrentName(self) -> str:
        """当前主题名称"""
        return self._current_theme

    def getDisplayNames(self) -> Dict[str, str]:
        """所有主题的显示名称"""
        return {name: data.get("display_name", name) for name, data in self._themes.items()}

    @staticmethod
    def instance():
        if ThemeManager._instance is None:
            ThemeManager._instance = ThemeManager()
        return ThemeManager._instance
