"""配置管理器 - JSON配置文件读写"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from PySide6.QtCore import QObject, Signal, Slot

from core.event_bus import EventBus, EventType
from utils.app_dir import get_data_dir
from utils.logger import logger


def _get_base_dir():
    """获取项目根目录（兼容开发环境和 PyInstaller onefile 模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


class ConfigManager(QObject):
    """配置管理器单例"""

    _instance = None
    configChanged = Signal(str, str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._config_dir = self._getConfigDir()
        self._cache: Dict[str, Dict] = {}
        self._loadAllConfigs()
        self._initialized = True

    def _getConfigDir(self) -> Path:
        """获取用户可写的配置目录（持久化保存用）"""
        return get_data_dir() / "config"

    def _getPackagedConfigDir(self) -> Path:
        """获取打包时自带的默认配置目录（只读）"""
        return _get_base_dir() / "config"

    def _loadAllConfigs(self):
        """加载所有配置文件"""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # 1) 加载用户已保存的配置
        for config_file in self._config_dir.glob("*.json"):
            section = config_file.stem
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._cache[section] = json.load(f)
            except Exception as e:
                logger.warning("[ConfigManager] 加载配置失败 %s: %s", config_file, e)
                self._cache[section] = {}

        # 2) 缺少默认配置时，从打包目录复制或生成
        pkg_dir = self._getPackagedConfigDir()
        defaults = {
            "app_config": self._defaultAppConfig,
            "hotkeys": self._defaultHotkeyConfig,
        }
        for section, default_fn in defaults.items():
            if section not in self._cache or not self._cache[section]:
                pkg_file = pkg_dir / f"{section}.json"
                if pkg_file.exists():
                    try:
                        with open(pkg_file, "r", encoding="utf-8") as f:
                            self._cache[section] = json.load(f)
                    except Exception as e:
                        logger.warning("[ConfigManager] 加载默认配置失败 %s: %s", pkg_file, e)
                        self._cache[section] = default_fn()
                else:
                    self._cache[section] = default_fn()
                self._saveConfig(section)

    def _defaultAppConfig(self) -> Dict:
        """默认应用配置"""
        return {
            "theme": "dark",
            "language": "zh_CN",
            "save_path": str(Path.home() / "Pictures" / "Screenshots"),
            "file_format": "PNG",
            "auto_copy": True,
            "capture_mode": "fullscreen",
            "toolbar_docked": False,
            "max_history": 50,
            "watermark": {
                "default_text": "机密文件",
                "default_opacity": 25,
                "default_size": 52,
                "default_rotation": 28,
                "default_color": "#888888"
            }
        }

    def _defaultHotkeyConfig(self) -> Dict:
        """默认快捷键配置"""
        return {
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

    @Slot(str, str, result="QVariant")
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._cache.get(section, {}).get(key, default)

    @Slot(str, str, "QVariant")
    def set(self, section: str, key: str, value: Any):
        """设置配置值"""
        if section not in self._cache:
            self._cache[section] = {}
        self._cache[section][key] = value
        self._saveConfig(section)

        # 发送事件
        self.configChanged.emit(section, key)
        EventBus.instance().publish(EventType.CONFIG_CHANGED, {
            "section": section, "key": key, "value": value
        })

    def getSection(self, section: str) -> Dict:
        """获取整个配置段落"""
        return self._cache.get(section, {})

    def _saveConfig(self, section: str):
        """保存配置到文件"""
        config_file = self._config_dir / f"{section}.json"
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self._cache[section], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[ConfigManager] 保存配置失败: %s", e)

    @staticmethod
    def instance():
        if ConfigManager._instance is None:
            ConfigManager._instance = ConfigManager()
        return ConfigManager._instance
