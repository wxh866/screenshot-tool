"""全屏截图引擎"""
import time
import tempfile
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication, QScreen
from PIL import Image

from models.screenshot import ScreenshotData, CaptureMode
from utils.logger import logger
from utils.image_utils import pixmapToPil


class FullscreenCapture(QObject):
    """全屏截图 - 使用QScreen.grabWindow()"""

    def capture(self) -> ScreenshotData:
        """捕获全屏截图"""
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                logger.error("无法获取主屏幕")
                return None

            pixmap = screen.grabWindow(0)

            if pixmap.isNull():
                logger.error("截图为空")
                return None

            # 转换为Pillow Image
            image = pixmapToPil(pixmap)

            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix=".png", prefix="screenshot_", delete=False) as tmp:
                temp_path = tmp.name
            image.save(temp_path)

            data = ScreenshotData(
                image_path=temp_path,
                capture_mode=CaptureMode.FULLSCREEN,
                width=image.width,
                height=image.height,
                timestamp=time.time(),
                dpi_scale=1.0
            )

            logger.info("全屏截图完成: %dx%d", image.width, image.height)
            return data

        except Exception as e:
            logger.error("全屏截图失败: %s", e)
            return None
