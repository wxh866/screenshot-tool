"""截图控制器 - QML与截图引擎的桥接层"""
import sys
import time
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QRect, QUrl, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Qt


def _get_base_dir():
    """获取项目根目录（兼容开发环境和 PyInstaller onefile 模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

from core.capture_service import ScreenshotEngine
from core.event_bus import EventBus, EventType
from models.screenshot import ScreenshotData, CaptureMode
from utils.logger import logger
from utils.image_utils import pixmapToPil


class ScreenshotController(QObject):
    """截图控制器 - 暴露给QML的所有截图操作"""

    # 信号：截图完成通知QML
    screenshotReady = Signal(str, int, int)   # image_path, width, height
    captureStarted = Signal(str)               # capture_mode
    captureCancelled = Signal()
    editorRequested = Signal(str, int, int)    # image_path, width, height

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = ScreenshotEngine()
        self._overlay_window = None
        self._editor_window = None
        self._current_data: ScreenshotData = None
        self._showing_overlay = False  # 防止覆盖层重复创建
        self._virtual_origin = (0, 0)   # 覆盖层虚拟左上角（多屏）

        # 连接信号
        self._engine.captureFinished.connect(self._onCaptureFinished)

        # 订阅事件总线
        EventBus.instance().subscribe(
            EventType.SCREENSHOT_CAPTURED,
            self._onScreenshotCaptured
        )

    # ========== QML可调用的Slot ==========

    @Slot(result="QVariant")
    def captureFullscreen(self):
        """全屏截图"""
        logger.info("[Controller] 全屏截图")
        self.captureStarted.emit("fullscreen")
        result = self._engine.capture(CaptureMode.FULLSCREEN)
        if result:
            return {
                "path": result.image_path,
                "width": result.width,
                "height": result.height
            }
        return None

    @Slot()
    def captureRegion(self):
        """区域截图 - 显示截图覆盖层"""
        logger.info("[Controller] 区域截图")

        # 隐藏主窗口
        self.captureStarted.emit("region")

        # 延迟到下一事件循环再创建覆盖层，让 Main.qml 的 captureStarted 槽先隐藏主窗口
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._showRegionOverlay)

    @Slot(result="QVariant")
    def captureWindow(self):
        """窗口截图 - 截取鼠标下的窗口"""
        logger.info("[Controller] 窗口截图")
        self.captureStarted.emit("window")
        result = self._engine.capture(CaptureMode.WINDOW)
        if result:
            return {
                "path": result.image_path,
                "width": result.width,
                "height": result.height
            }
        return None

    @Slot()
    def captureScrolling(self):
        """滚动截图"""
        logger.info("[Controller] 滚动截图")
        self.captureStarted.emit("scrolling")
        self._engine.capture(CaptureMode.SCROLLING)

    @Slot()
    def cancelCapture(self):
        """取消当前截图"""
        logger.info("[Controller] 取消截图")
        if hasattr(self._engine, '_capturers'):
            scrolling = self._engine._capturers.get(CaptureMode.SCROLLING)
            if scrolling and scrolling._is_capturing:
                scrolling.stopCapture()

        self._hideOverlay()
        self.captureCancelled.emit()

    # ========== 覆盖层管理 ==========

    def _showRegionOverlay(self):
        """显示区域截图覆盖层"""
        if self._showing_overlay:
            logger.warning("[Controller] 覆盖层已在显示中，忽略重复请求")
            return
        self._showing_overlay = True
        logger.info("[Controller] 开始显示区域覆盖层")

        if self._overlay_window is not None:
            logger.info("[Controller] 关闭旧覆盖层")
            self._overlay_window.close()
            self._overlay_window.deleteLater()
            self._overlay_window = None

        try:
            # 获取所有屏幕（多显示器支持，参考 Flameshot 多屏捕获）
            screens = QGuiApplication.screens()
            if not screens:
                screens = [QGuiApplication.primaryScreen()]
            from utils.capture_geometry import ScreenGeom, virtual_bounding_geometry
            geoms = [
                ScreenGeom(
                    s.geometry().x(), s.geometry().y(),
                    s.geometry().width(), s.geometry().height(),
                    s.devicePixelRatio()
                )
                for s in screens
            ]
            virt = virtual_bounding_geometry(geoms)
            self._virtual_origin = (virt.x, virt.y)
            logger.info("[Controller] 虚拟屏幕几何: %s", virt)

            # 截取全部屏幕并合成为覆盖层背景（保证多屏下背景完整）
            logger.info("[Controller] 合成全屏背景...")
            from PIL import Image
            bg = Image.new("RGBA", (virt.width, virt.height), (0, 0, 0, 255))
            for s, g in zip(screens, geoms):
                pm = s.grabWindow(0)
                if pm.isNull():
                    continue
                im = pixmapToPil(pm)  # 现保留 alpha
                bg.paste(im, (g.x - virt.x, g.y - virt.y))
            bg_path = self._saveTempImage(bg)
            logger.info("[Controller] 背景已保存: %s", bg_path)

            # 创建透明全屏窗口（铺满虚拟屏幕并集）
            logger.info("[Controller] 创建 QQuickView 覆盖层...")
            self._overlay_window = QQuickView()
            self._overlay_window.setFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self._overlay_window.setColor(Qt.transparent)
            self._overlay_window.setResizeMode(QQuickView.SizeRootObjectToView)
            self._overlay_window.setGeometry(virt.x, virt.y, virt.width, virt.height)

            # 加载QML覆盖层
            qml_path = _get_base_dir() / "views" / "RegionOverlay.qml"
            logger.info("[Controller] 加载覆盖层 QML: %s", qml_path)
            self._overlay_window.setSource(QUrl.fromLocalFile(str(qml_path)))

            # QML的rootObject暴露信号给Python并设置背景图
            root = self._overlay_window.rootObject()
            if root:
                logger.info("[Controller] 连接覆盖层信号")
                root.regionConfirmed.connect(self._onRegionConfirmed)
                root.captureCancelled.connect(self.cancelCapture)
                root.setProperty("backgroundPath", bg_path)
            else:
                logger.error("[Controller] 覆盖层 rootObject 为空")
                self._showing_overlay = False
                return

            logger.info("[Controller] 显示覆盖层")
            self._overlay_window.show()
            logger.info("[Controller] 覆盖层显示完成")
        finally:
            self._showing_overlay = False

    def _hideOverlay(self):
        """隐藏覆盖层"""
        if self._overlay_window:
            self._overlay_window.close()
            self._overlay_window.deleteLater()
            self._overlay_window = None
            logger.info("[Controller] 覆盖层已隐藏")

    def _saveTempPixmap(self, pixmap: QPixmap) -> str:
        """保存QPixmap到临时文件"""
        with tempfile.NamedTemporaryFile(suffix=".png", prefix="overlay_bg_", delete=False) as tmp:
            temp_path = tmp.name
        pixmap.save(temp_path, "PNG")
        return temp_path

    def _saveTempImage(self, image) -> str:
        """保存Pillow Image到临时文件（合成多屏背景用）"""
        with tempfile.NamedTemporaryFile(suffix=".png", prefix="overlay_bg_", delete=False) as tmp:
            temp_path = tmp.name
        image.save(temp_path, "PNG")
        return temp_path

    # ========== 内部信号处理 ==========

    @Slot(int, int, int, int)
    def _onRegionConfirmed(self, x: int, y: int, w: int, h: int):
        """区域截图确认 - 来自QML覆盖层"""
        logger.info("[Controller] 区域确认: (%d,%d) %dx%d", x, y, w, h)

        self._hideOverlay()

        if w < 10 or h < 10:
            logger.warning("选区太小，取消截图")
            self.captureCancelled.emit()
            return

        # 延迟到下一个事件循环迭代执行截图，
        # 避免在overlay信号回调中创建新窗口导致崩溃
        QTimer.singleShot(0, lambda: self._doRegionCapture(x, y, w, h))

    def _doRegionCapture(self, x: int, y: int, w: int, h: int):
        """执行区域截图（在overlay完全销毁后调用）"""
        from utils.capture_geometry import (
            ScreenGeom, device_rect, clamp_rect_to_geometry,
            virtual_bounding_geometry, screen_index_for_point,
        )

        # QML 坐标为相对于覆盖层（虚拟屏幕并集）左上角的逻辑像素，
        # 先换算到绝对逻辑坐标，再选包含该点的屏幕抓取
        abs_x = x + self._virtual_origin[0]
        abs_y = y + self._virtual_origin[1]

        screens = QGuiApplication.screens()
        if not screens:
            screens = [QGuiApplication.primaryScreen()]
        geoms = [
            ScreenGeom(s.geometry().x(), s.geometry().y(),
                       s.geometry().width(), s.geometry().height(),
                       s.devicePixelRatio())
            for s in screens
        ]
        idx = screen_index_for_point((abs_x, abs_y), geoms)
        target = geoms[idx]
        qscreen = screens[idx]

        # 相对目标屏幕左上角的逻辑坐标
        local_x = abs_x - target.x
        local_y = abs_y - target.y

        # 逻辑 → 设备像素（HiDPI），再裁剪到屏幕设备几何
        dev = device_rect((local_x, local_y, w, h), target.dpr)
        dev_geom = ScreenGeom(0, 0,
                              int(target.width * target.dpr),
                              int(target.height * target.dpr))
        dev = clamp_rect_to_geometry(dev, dev_geom)

        pixmap = qscreen.grabWindow(0, dev[0], dev[1], dev[2], dev[3])

        if pixmap.isNull():
            logger.error("区域截图失败：空pixmap（坐标越界？）")
            self.captureCancelled.emit()
            return

        # 转换为Pillow并保存
        image = pixmapToPil(pixmap)
        with tempfile.NamedTemporaryFile(suffix=".png", prefix="screenshot_", delete=False) as tmp:
            temp_path = tmp.name
        image.save(temp_path)

        data = ScreenshotData(
            image_path=temp_path,
            capture_mode=CaptureMode.REGION,
            width=image.width,
            height=image.height,
            timestamp=time.time()
        )

        self._current_data = data
        self.screenshotReady.emit(temp_path, image.width, image.height)

    def _onCaptureFinished(self, data: ScreenshotData):
        """截图引擎完成回调"""
        if data:
            self._current_data = data
            self.screenshotReady.emit(data.image_path, data.width, data.height)
            logger.info("[Controller] 截图完成: %dx%d", data.width, data.height)
        else:
            logger.warning("[Controller] 截图结果为空")
            self.captureCancelled.emit()

    def _onScreenshotCaptured(self, data):
        """事件总线通知"""
        if isinstance(data, ScreenshotData):
            self._current_data = data
        logger.debug("[Controller] 收到截图事件")

    # ========== 截图数据访问 ==========

    @Slot(result="QVariant")
    def getCurrentScreenshot(self):
        """获取当前截图数据"""
        if self._current_data:
            return {
                "path": self._current_data.image_path,
                "width": self._current_data.width,
                "height": self._current_data.height,
                "mode": self._current_data.capture_mode.value
            }
        return None

    @Slot(result=str)
    def getCurrentPath(self):
        """获取当前截图路径"""
        return self._current_data.image_path if self._current_data else ""

    @Slot(result=str)
    def browseFolder(self):
        """打开原生文件夹选择对话框"""
        folder = QFileDialog.getExistingDirectory(
            None, "选择保存目录",
            self._lastSaveDir(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        return folder if folder else ""

    def _lastSaveDir(self) -> str:
        """获取上次保存目录"""
        from core.config_manager import ConfigManager
        path = ConfigManager.instance().get("app_config", "save_path", "")
        if path:
            return path
        from pathlib import Path
        return str(Path.home() / "Pictures")
