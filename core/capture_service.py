"""截图引擎 - 统一截图入口"""
from typing import Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from models.screenshot import ScreenshotData, CaptureMode
from core.event_bus import EventBus, EventType
from utils.logger import logger
from utils.image_utils import pilToPixmap, pixmapToPil


class ScreenshotEngine(QObject):
    """截图引擎 - 管理4种截图模式"""

    captureFinished = Signal(object)  # ScreenshotData

    def __init__(self):
        super().__init__()
        self._current_mode = CaptureMode.FULLSCREEN
        self._capturers = {}
        self._initCapturers()

    def _initCapturers(self):
        """初始化各截图模式处理器"""
        try:
            from engines.capture.fullscreen import FullscreenCapture
            self._capturers[CaptureMode.FULLSCREEN] = FullscreenCapture()
        except Exception as e:
            logger.warning("全屏截图模块加载失败: %s", e)

        try:
            from engines.capture.region import RegionCapture
            self._capturers[CaptureMode.REGION] = RegionCapture()
        except Exception as e:
            logger.warning("区域截图模块加载失败: %s", e)

        try:
            from engines.capture.window import WindowCapture
            self._capturers[CaptureMode.WINDOW] = WindowCapture()
        except Exception as e:
            logger.warning("窗口截图模块加载失败: %s", e)

        try:
            from engines.capture.scrolling import ScrollingCapture
            self._capturers[CaptureMode.SCROLLING] = ScrollingCapture()
        except Exception as e:
            logger.warning("滚动截图模块加载失败: %s", e)

    def capture(self, mode: CaptureMode = None):
        """执行截图"""
        target_mode = mode or self._current_mode
        capturer = self._capturers.get(target_mode)

        if capturer is None:
            logger.error("截图模式不可用: %s", target_mode)
            return None

        logger.info("开始截图 - 模式: %s", target_mode.value)
        result = capturer.capture()

        if result:
            EventBus.instance().publish(EventType.SCREENSHOT_CAPTURED, result)
            self.captureFinished.emit(result)

        return result

    def setMode(self, mode: CaptureMode):
        """设置截图模式"""
        self._current_mode = mode
        EventBus.instance().publish(EventType.SCREENSHOT_MODE_CHANGED, mode.value)
        logger.info("截图模式切换: %s", mode.value)

    def getAvailableModes(self) -> list:
        """获取可用截图模式"""
        return list(self._capturers.keys())
