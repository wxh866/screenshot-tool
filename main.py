"""截图软件 - 主入口文件"""
import sys
import os
import io
import traceback
from pathlib import Path

# Windows 控制台默认 GBK，日志含非 ASCII 字符会抛 UnicodeEncodeError。
# 重设标准流为 UTF-8，作为编码异常的全局安全网（不影响已修复的日志内容）。
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _get_base_dir():
    """获取项目根目录（兼容开发环境和 PyInstaller onefile 模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


BASE_DIR = _get_base_dir()


def _get_exe_dir():
    """获取EXE所在目录（开发环境返回项目根目录）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _show_crash_dialog(title: str, message: str):
    """弹窗显示崩溃信息（GUI 模式下无控制台时必须用）"""
    # 无论是否弹窗，都先写文件，方便用户发送
    _write_crash_log(title, message)

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        # 确保至少有一个 QApplication 实例
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        pass


def _write_crash_log(title: str, message: str):
    """把崩溃信息写入EXE目录的 crash_log.txt"""
    try:
        exe_dir = _get_exe_dir()
        crash_log = exe_dir / "crash_log.txt"
        with open(crash_log, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {title}\n")
            f.write(message)
            f.write("\n")
    except Exception:
        pass


# ---- 最早阶段导入：捕获所有导入错误 ----
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
    from PySide6.QtCore import QUrl, QObject, Qt
    from PySide6.QtQuickControls2 import QQuickStyle
except Exception as e:
    _show_crash_dialog("PySide6 导入失败", f"无法加载 PySide6 模块:\n{e}\n\n请确认已正确安装依赖。")
    sys.exit(-1)

try:
    from core.event_bus import EventBus
    from core.config_manager import ConfigManager
    from core.undo_manager import UndoManager
    from core.capture_service import ScreenshotEngine
    from themes.theme_manager import ThemeManager
    from controllers.screenshot_controller import ScreenshotController
    from controllers.editor_controller import EditorController
    from controllers.history_controller import HistoryController
    from utils.logger import logger
    from utils.hotkey_manager import HotkeyManager
except Exception as e:
    _show_crash_dialog("模块导入失败", f"无法加载项目模块:\n{traceback.format_exc()}")
    sys.exit(-1)


class ScreenshotApp(QObject):
    """截图软件应用主类"""

    def __init__(self):
        super().__init__()
        try:
            self.app = QApplication(sys.argv)
            QQuickStyle.setStyle("Fusion")
            # 全局禁用自动退出——区域截图时主窗口会被隐藏，由 Main.qml onClosing 手动调用 Qt.quit()
            self.app.setQuitOnLastWindowClosed(False)
        except Exception as e:
            _show_crash_dialog("QApplication 初始化失败", traceback.format_exc())
            raise

        self._screenshot_controller = None
        self._editor_engine = None
        self._editor_controller = None
        self._main_engine = None
        self._main_window = None
        self._hotkey_mgr = None
        self._native_filter = None  # 保持 NativeHotkeyFilter 引用防止 GC
        self._is_capturing = False  # 防止全局热键重入
        self._opening_editor = False  # 防止 _openEditor 重入

        steps = [
            ("QML 引擎初始化", self._initQmlEngine),
            ("应用信息设置", self._setupAppInfo),
            ("单例初始化", self._setupSingletons),
            ("控制器注册", self._registerControllers),
            ("QML 加载", self._loadQML),
        ]
        for name, fn in steps:
            try:
                fn()
            except Exception as e:
                _show_crash_dialog(f"{name}失败", traceback.format_exc())
                raise

    def _initQmlEngine(self):
        self._main_engine = QQmlApplicationEngine()
        # 捕获 QML 警告/错误
        self._main_engine.warnings.connect(lambda msgs: [
            logger.warning("QML: %s", str(m)) for m in (msgs if isinstance(msgs, list) else [msgs])
        ])

    def _setupAppInfo(self):
        """设置应用信息和QML环境"""
        self.app.setApplicationName("截图软件")
        self.app.setApplicationVersion("5.0")
        self.app.setOrganizationName("wxh866")

        # 打包模式下禁用QML磁盘缓存，避免文件系统权限问题
        if getattr(sys, 'frozen', False):
            os.environ["QML_DISABLE_DISK_CACHE"] = "1"

        # 加载初始主题
        config = ConfigManager.instance()
        theme_name = config.get("app_config", "theme", "dark")
        ThemeManager.instance().switchTheme(theme_name)

        logger.info("截图软件启动 - 主题: %s", theme_name)

    def _setupSingletons(self):
        """初始化单例"""
        EventBus.instance()
        ConfigManager.instance()
        UndoManager.instance()
        ThemeManager.instance()

    def _registerControllers(self):
        """注册QML控制器"""
        root_context = self._main_engine.rootContext()

        # 截图控制器
        self._screenshot_controller = ScreenshotController()
        root_context.setContextProperty("ScreenshotController", self._screenshot_controller)

        # 主题管理器
        root_context.setContextProperty("ThemeManager", ThemeManager.instance())

        # 配置管理器
        root_context.setContextProperty("ConfigManager", ConfigManager.instance())

        # 历史控制器 (主窗口用)
        self._history_controller = HistoryController()
        root_context.setContextProperty("HistoryController", self._history_controller)

        # 连接截图完成信号 → 打开编辑器
        self._screenshot_controller.screenshotReady.connect(self._onScreenshotReady)

        # 连接历史记录选择信号 → 打开编辑器
        self._history_controller.historyItemSelected.connect(self._onScreenshotReady)

        # 全局热键
        self._setupGlobalHotkeys()

        logger.info("QML控制器注册完成")

    def _setupGlobalHotkeys(self):
        """注册全局热键 — 使用 Windows RegisterHotKey（NativeEventFilter，主线程零延迟）"""
        # 需要主窗口的 winId() 来注册系统级热键
        # 此时 QML 可能还未加载完成，稍后在 _loadQML 后补充初始化
        self._hotkey_mgr = HotkeyManager()  # 无窗口时只加载配置
        logger.info("[快捷键] HotkeyManager 配置已加载（热键将在QML窗口就绪后激活）")

    def _onGlobalHotkey(self, action: str):
        """全局热键处理 — NativeEventFilter 保证已在主线程"""
        logger.info("[快捷键] 触发: %s (正在截图=%s, 正在开编辑器=%s)",
                    action, self._is_capturing, self._opening_editor)

        if self._is_capturing:
            logger.warning("[快捷键] 忽略 [%s]：已有截图进行中", action)
            return

        try:
            self._is_capturing = True

            if action == "capture_fullscreen":
                self._screenshot_controller.captureFullscreen()
            elif action == "capture_region":
                self._screenshot_controller.captureRegion()
            elif action == "capture_window":
                self._screenshot_controller.captureWindow()
            else:
                logger.warning("[快捷键] 未知动作: %s", action)

        except Exception as e:
            logger.error("[快捷键] 处理失败 [%s]: %s", action, e, exc_info=True)
        finally:
            self._is_capturing = False

    def _loadQML(self):
        """加载QML界面"""
        qml_dir = BASE_DIR / "views"
        main_qml = qml_dir / "Main.qml"

        if main_qml.exists():
            self._main_engine.load(QUrl.fromLocalFile(str(main_qml)))
        else:
            logger.error("QML文件不存在: %s", main_qml)
            sys.exit(-1)

        if not self._main_engine.rootObjects():
            logger.error("QML加载失败")
            sys.exit(-1)

        # 保存主窗口引用
        self._main_window = self._main_engine.rootObjects()[0]

        # 主窗口就绪后激活全局热键（需要 winId 才能调用 RegisterHotKey）
        self._activateGlobalHotkeys()

    def _activateGlobalHotkeys(self):
        """激活全局热键（在主窗口 QML 加载完成后调用）"""
        if self._hotkey_mgr is None:
            return

        from platforms.native_hotkey import NativeHotkeyFilter
        from PySide6.QtWidgets import QApplication

        # RegisterHotKey 传 HWND=None，热键不与特定窗口绑定，
        # 即使主窗口隐藏（截图时）热键仍然有效
        native_filter = NativeHotkeyFilter(self._onGlobalHotkey)

        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(native_filter)
        else:
            logger.error("[快捷键] QApplication 不可用，无法安装 NativeEventFilter")
            return

        self._native_filter = native_filter  # 保持引用防止 GC
        self._hotkey_mgr._native_filter = native_filter

        # 注册截图类全局热键
        actions = ["capture_fullscreen", "capture_region", "capture_window"]
        for action in actions:
            self._hotkey_mgr.registerGlobalHotkey(action)

        registered = len(native_filter._registered)
        logger.info("[快捷键] 全局热键激活完成: %d/3 注册成功 (HWND=None)",
                    registered)
        if registered == 0:
            logger.error("[快捷键] 所有热键注册均失败！检查是否有其他程序占用 Ctrl+Shift+F/R/W")

        # 退出时注销热键
        self.app.aboutToQuit.connect(native_filter.unregisterAll)

    def _onScreenshotReady(self, image_path: str, width: int, height: int):
        """截图完成后打开编辑器"""
        logger.info("截图就绪: %s (%dx%d)", image_path, width, height)
        self._openEditor(image_path, width, height)

    def _openEditor(self, image_path: str, width: int, height: int):
        """打开截图编辑器窗口"""
        # 防重入：processEvents() 循环中可能触发全局热键再次进入此方法
        if self._opening_editor:
            logger.warning("[_openEditor] 重入被阻止（已有编辑器正在打开）")
            return
        self._opening_editor = True

        try:
            # 关闭旧编辑器
            if self._editor_engine is not None:
                if self._editor_controller:
                    try:
                        self._editor_controller.editorClosed.disconnect(self._onEditorClosed)
                    except Exception:
                        pass
                    self._editor_controller.editorClosed.emit()
                    self._editor_controller = None
                old_engine = self._editor_engine
                self._editor_engine = None
                old_engine.deleteLater()

            # 创建编辑器控制器
            self._editor_controller = EditorController()
            self._editor_controller.setBaseImage(image_path)
            self._editor_controller.editorClosed.connect(self._onEditorClosed)

            # QQmlApplicationEngine + processEvents 等待异步加载完成
            self._editor_engine = QQmlApplicationEngine()
            root_ctx = self._editor_engine.rootContext()
            root_ctx.setContextProperty("EditorController", self._editor_controller)
            root_ctx.setContextProperty("ThemeManager", ThemeManager.instance())

            qml_path = BASE_DIR / "views" / "EditorView.qml"
            logger.info("编辑器QML路径: %s (exists=%s)", qml_path, qml_path.exists())
            self._editor_engine.load(QUrl.fromLocalFile(str(qml_path)))

            # 循环处理事件直到 QML 加载完成（最多等 2 秒）
            for i in range(200):
                QApplication.processEvents()
                if self._editor_engine.rootObjects():
                    break
                if i > 0 and i % 50 == 0:
                    logger.info("等待QML加载... (%d/200)", i)

            roots = self._editor_engine.rootObjects()
            if not roots:
                logger.error("编辑器QML加载失败（超时）")
                self._onEditorClosed()
                return

            root = roots[0]
            logger.info("QML根对象: %s", root.metaObject().className())

            root.setProperty("imagePath", image_path)
            root.setProperty("imageWidth", width)
            root.setProperty("imageHeight", height)

            # 设置窗口大小和位置
            screen = self.app.primaryScreen()
            screen_rect = screen.availableGeometry()
            max_w = int(screen_rect.width() * 0.9)
            max_h = int(screen_rect.height() * 0.9)
            sidebar_w = 220  # 右侧面板宽度
            win_w = min(width + sidebar_w + 40, max_w)
            win_h = min(height + 100, max_h)

            root.setProperty("x", max(0, (screen_rect.width() - win_w) // 2))
            root.setProperty("y", max(0, (screen_rect.height() - win_h) // 2))
            root.setProperty("width", win_w)
            root.setProperty("height", win_h)

            # 显式显示窗口（EXE环境下ApplicationWindow可能不自启）
            root.setProperty("visible", True)
            root.setProperty("visibility", 1)  # WindowVisible = 1

            logger.info("编辑器窗口已创建")
        finally:
            self._opening_editor = False

    def _onEditorClosed(self):
        """编辑器关闭后的清理"""
        logger.info("编辑器关闭，清理资源")
        if self._editor_engine:
            old_engine = self._editor_engine
            self._editor_engine = None
            old_engine.deleteLater()
        if self._editor_controller:
            try:
                self._editor_controller.editorClosed.disconnect(self._onEditorClosed)
            except Exception:
                pass
            self._editor_controller = None

        # 恢复显示主窗口
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()

        # 重新注册全局热键 — 确保编辑器关闭后快捷键仍可用
        self._reregisterHotkeys()

    def _reregisterHotkeys(self):
        """重新注册全局热键（防止热键在编辑器开关后失效）"""
        if self._native_filter is None or self._hotkey_mgr is None:
            return

        # 先全部注销
        self._native_filter.unregisterAll()

        # 重新注册
        actions = ["capture_fullscreen", "capture_region", "capture_window"]
        for action in actions:
            self._hotkey_mgr.registerGlobalHotkey(action)

        registered = len(self._native_filter._registered)
        logger.info("[快捷键] 热键已重新注册: %d/3 成功", registered)

    def run(self) -> int:
        """运行应用"""
        logger.info("应用进入主循环")
        return self.app.exec()


def main():
    """程序入口"""
    try:
        screenshot_app = ScreenshotApp()
        logger.info("应用进入主循环")
        exit_code = screenshot_app.run()
        logger.info("应用退出 - 代码: %d", exit_code)
        return exit_code
    except SystemExit as e:
        return e.code if e.code is not None else -1
    except Exception as e:
        tb = traceback.format_exc()
        logger.critical("应用崩溃: %s", e, exc_info=True)
        _write_crash_log("应用崩溃", tb)
        _show_crash_dialog("应用崩溃", tb)
        return -1


if __name__ == "__main__":
    sys.exit(main())
