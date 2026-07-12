"""控制器层 - QML与Python逻辑的桥接"""
from controllers.screenshot_controller import ScreenshotController
from controllers.editor_controller import EditorController
from controllers.history_controller import HistoryController

__all__ = ['ScreenshotController', 'EditorController', 'HistoryController']
