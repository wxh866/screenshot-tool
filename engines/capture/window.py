"""窗口截图引擎"""
import time
import tempfile
from typing import List, Dict
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PIL import Image

from models.screenshot import ScreenshotData, CaptureMode
from utils.logger import logger
from utils.image_utils import pixmapToPil


class WindowCapture(QObject):
    """窗口截图 - 选择可见窗口并截图"""

    windowListReady = Signal(list)   # 窗口列表
    windowSelected = Signal(str)     # 窗口标题

    def __init__(self):
        super().__init__()
        self._windows = []
        self._tryImportWin32()

    def _tryImportWin32(self):
        """尝试导入win32模块"""
        try:
            import win32gui
            import win32con
            self._has_win32 = True
        except ImportError:
            self._has_win32 = False
            logger.warning("win32模块不可用，窗口截图功能受限")

    def enumerateWindows(self) -> List[Dict]:
        """枚举所有可见窗口"""
        if not self._has_win32:
            logger.warning("无win32支持，无法枚举窗口")
            return []

        import win32gui
        windows = []

        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "rect": rect,
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1]
                    })
            return True

        win32gui.EnumWindows(enum_callback, None)
        self._windows = windows
        self.windowListReady.emit(windows)
        logger.info("枚举窗口: %d个", len(windows))
        return windows

    def captureWindow(self, hwnd=None, title=None) -> ScreenshotData:
        """截取指定窗口"""
        if not self._has_win32:
            return None

        import win32gui
        from PySide6.QtGui import QPixmap

        # 查找窗口
        if hwnd is None and title:
            hwnd = win32gui.FindWindow(None, title)

        if not hwnd:
            logger.error("找不到目标窗口")
            return None

        try:
            rect = win32gui.GetWindowRect(hwnd)
            # GetWindowRect 返回物理(设备)像素；grabWindow 也按设备像素抓取。
            # 需先按窗口中心选对所在屏幕，否则副屏窗口会被主屏 grabWindow 越界抓取。
            phys_w = rect[2] - rect[0]
            phys_h = rect[3] - rect[1]
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2

            target = None
            for s in QGuiApplication.screens():
                gx, gy = s.geometry().x(), s.geometry().y()
                gw, gh = s.geometry().width(), s.geometry().height()
                dpr = s.devicePixelRatio()
                px0, py0 = gx * dpr, gy * dpr
                px1, py1 = px0 + gw * dpr, py0 + gh * dpr
                if px0 <= cx < px1 and py0 <= cy < py1:
                    target = s
                    break
            if target is None:
                target = QGuiApplication.primaryScreen()
                dpr = target.devicePixelRatio()

            # 相对该屏幕物理(设备)左上角的偏移
            gx, gy = target.geometry().x() * dpr, target.geometry().y() * dpr
            dev_x = rect[0] - gx
            dev_y = rect[1] - gy

            # 裁剪到屏幕设备几何，避免越界空图
            from utils.capture_geometry import clamp_rect_to_geometry, ScreenGeom
            phys_w = max(1, phys_w)
            phys_h = max(1, phys_h)
            dev_x, dev_y, phys_w, phys_h = clamp_rect_to_geometry(
                (dev_x, dev_y, phys_w, phys_h),
                ScreenGeom(0, 0, int(target.geometry().width() * dpr),
                           int(target.geometry().height() * dpr)),
            )

            pixmap = target.grabWindow(0, dev_x, dev_y, phys_w, phys_h)

            image = pixmapToPil(pixmap)

            with tempfile.NamedTemporaryFile(suffix=".png", prefix="screenshot_", delete=False) as tmp:
                temp_path = tmp.name
            image.save(temp_path)

            data = ScreenshotData(
                image_path=temp_path,
                capture_mode=CaptureMode.WINDOW,
                width=image.width,
                height=image.height,
                timestamp=time.time()
            )

            logger.info("窗口截图完成: %s", title or str(hwnd))
            return data

        except Exception as e:
            logger.error("窗口截图失败: %s", e)
            return None

    def capture(self) -> ScreenshotData:
        """启动窗口选择（默认截取当前鼠标下的窗口）"""
        if not self._has_win32:
            logger.warning("窗口截图需要win32支持")
            return None

        import win32gui
        import win32api

        # 获取鼠标下的窗口
        point = win32api.GetCursorPos()
        hwnd = win32gui.WindowFromPoint(point)
        hwnd = win32gui.GetAncestor(hwnd, win32gui.GA_ROOT)

        if hwnd:
            return self.captureWindow(hwnd=hwnd)

        return None
