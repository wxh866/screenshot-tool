"""Windows API工具函数"""
from typing import Optional, Tuple, List, Dict
from utils.logger import logger


_has_win32 = False
try:
    import win32gui
    import win32api
    import win32con
    _has_win32 = True
except ImportError:
    logger.warning("win32模块不可用")


def isWin32Available() -> bool:
    """检查win32模块是否可用"""
    return _has_win32


def getScreenSize() -> Tuple[int, int]:
    """获取屏幕尺寸"""
    if _has_win32:
        import win32api
        return win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
    return 1920, 1080  # 默认值


def getVirtualScreenRect() -> Tuple[int, int, int, int]:
    """获取虚拟桌面矩形（支持多显示器）"""
    if _has_win32:
        import win32api
        x = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        y = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        w = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        h = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        return x, y, w, h
    return 0, 0, 1920, 1080


def findWindowAtPoint(x: int, y: int) -> Optional[int]:
    """查找指定坐标处的窗口"""
    if not _has_win32:
        return None

    import win32gui
    hwnd = win32gui.WindowFromPoint((x, y))
    hwnd = win32gui.GetAncestor(hwnd, win32gui.GA_ROOT)
    return hwnd


def getWindowRect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """获取窗口矩形"""
    if not _has_win32:
        return None

    import win32gui
    try:
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


def getWindowTitle(hwnd: int) -> Optional[str]:
    """获取窗口标题"""
    if not _has_win32:
        return None

    import win32gui
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return None
