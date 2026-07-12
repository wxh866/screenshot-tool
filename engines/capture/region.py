"""区域截图引擎"""
import time
import tempfile
from PySide6.QtCore import QObject, Signal, QRect
from PySide6.QtGui import QGuiApplication

from models.screenshot import ScreenshotData, CaptureMode
from utils.logger import logger
from utils.image_utils import pixmapToPil


class RegionCapture(QObject):
    """区域截图 - 支持QML覆盖层或直接指定坐标"""

    regionSelected = Signal(QRect)

    def capture(self) -> ScreenshotData:
        """旧版接口：启动QWidget覆盖层选择"""
        # QML覆盖层方式已通过ScreenshotController实现
        # 此处保留作为fallback
        logger.warning("RegionCapture.capture() 已弃用，请使用 ScreenshotController")
        return None

    def captureRect(self, x: int, y: int, width: int, height: int) -> ScreenshotData:
        """直接按指定坐标截取区域

        Args:
            x, y: 左上角坐标
            width, height: 区域尺寸
        """
        if width < 5 or height < 5:
            logger.warning("选区太小: %dx%d", width, height)
            return None

        try:
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                logger.error("无法获取主屏幕")
                return None

            # HiDPI：QML/UI 坐标为逻辑像素，grabWindow 按设备像素抓取，
            # 需乘 devicePixelRatio（参考 Flameshot 分数缩放修复 #564/#4171）
            dpr = screen.devicePixelRatio()
            dev_x = round(x * dpr)
            dev_y = round(y * dpr)
            dev_w = round(width * dpr)
            dev_h = round(height * dpr)

            # 裁剪到屏幕设备几何，避免越界导致空图
            from utils.capture_geometry import clamp_rect_to_geometry, ScreenGeom
            gw = int(screen.geometry().width() * dpr)
            gh = int(screen.geometry().height() * dpr)
            dev_x, dev_y, dev_w, dev_h = clamp_rect_to_geometry(
                (dev_x, dev_y, dev_w, dev_h), ScreenGeom(0, 0, gw, gh)
            )

            pixmap = screen.grabWindow(0, dev_x, dev_y, dev_w, dev_h)

            if pixmap.isNull():
                logger.error("区域截图为空")
                return None

            image = pixmapToPil(pixmap)

            with tempfile.NamedTemporaryFile(suffix=".png", prefix="screenshot_", delete=False) as tmp:
                temp_path = tmp.name
            image.save(temp_path)

            data = ScreenshotData(
                image_path=temp_path,
                capture_mode=CaptureMode.REGION,
                width=image.width,
                height=image.height,
                timestamp=time.time(),
                dpi_scale=1.0
            )

            logger.info("区域截图完成: %dx%d at (%d,%d)", width, height, x, y)
            return data

        except Exception as e:
            logger.error("区域截图失败: %s", e)
            return None
