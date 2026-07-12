"""原生Windows热键 — RegisterHotKey + QAbstractNativeEventFilter

参考 CSDN 已验证的 PySide2/PySide6 全局热键实现：
https://blog.csdn.net/User287/article/details/131932393

关键设计：
- 只继承 QAbstractNativeEventFilter（不继承 QObject）
- 用 Python 回调替代 Qt Signal，避免生命周期问题
- RegisterHotKey 传 HWND=None（热键不与特定窗口绑定）
- nativeEventFilter 必须返回 (bool, int) 元组（PySide6 绑定层要求）
- 用 wintypes.MSG.from_address(message.__int__()) 解析消息
"""
import ctypes
import ctypes.wintypes
from typing import Dict, Callable

from PySide6.QtCore import QAbstractNativeEventFilter

from utils.logger import logger

# Win32 API 常量
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

VK_MAP = {
    "F": 0x46, "R": 0x52, "W": 0x57, "S": 0x53,
    "Z": 0x5A, "Y": 0x59, "C": 0x43,
    "A": 0x41, "B": 0x42, "D": 0x44, "E": 0x45,
    "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E,
    "O": 0x4F, "P": 0x50, "Q": 0x51, "T": 0x54,
    "U": 0x55, "V": 0x56, "X": 0x58,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "ESC": 0x1B, "DELETE": 0x2E, "SPACE": 0x20,
    "TAB": 0x09, "ENTER": 0x0D, "BACKSPACE": 0x08,
}


def parseSequence(sequence: str):
    """解析快捷键字符串为 (modifiers, vk)

    Example: "Ctrl+Shift+F" → (MOD_CONTROL | MOD_SHIFT, 0x46)
    """
    parts = [p.strip().upper() for p in sequence.split("+")]
    mod = 0
    vk = 0
    for p in parts:
        if p == "CTRL":
            mod |= MOD_CONTROL
        elif p == "SHIFT":
            mod |= MOD_SHIFT
        elif p == "ALT":
            mod |= MOD_ALT
        elif p == "WIN" or p == "META":
            mod |= MOD_WIN
        elif p in VK_MAP:
            vk = VK_MAP[p]
        else:
            logger.warning("[NativeHotkey] 无法解析按键: %s", p)
            return None, None
    return mod, vk


class NativeHotkeyFilter(QAbstractNativeEventFilter):
    """原生Windows热键过滤器

    参考 PySide6 已验证的实现方式：
    - nativeEventFilter 返回 (bool, int) 元组
    - 用 wintypes.MSG.from_address(message.__int__()) 转换消息
    - RegisterHotKey 用 HWND=None（不与特定窗口绑定）
    """

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback
        self._hotkey_id_counter = 1
        self._registered: Dict[int, str] = {}   # id → action
        self._action_map: Dict[str, int] = {}   # action → id
        self._user32 = ctypes.windll.user32
        logger.info("[NativeHotkey] 初始化完成（HWND=None，热键不与窗口绑定）")

    def registerHotkey(self, action: str, sequence: str) -> bool:
        """注册系统级热键（全局生效，窗口不可见时也有效）

        传 HWND=None，热键不绑定到特定窗口。
        这样即使主窗口隐藏（截图时），热键仍然有效。
        """
        mod, vk = parseSequence(sequence)
        if vk is None:
            logger.warning("[NativeHotkey] 无法解析热键序列: %s", sequence)
            return False

        # 先注销旧的同名热键
        if action in self._action_map:
            self.unregisterHotkey(action)

        hid = self._hotkey_id_counter
        self._hotkey_id_counter += 1

        # RegisterHotKey(hwnd=None, id, fsModifiers, vk) — 不绑定窗口
        result = self._user32.RegisterHotKey(None, hid, mod, vk)
        if result:
            self._registered[hid] = action
            self._action_map[action] = hid
            logger.info("[NativeHotkey] 注册成功: %s -> %s (id=%d)",
                        action, sequence, hid)
        else:
            err = ctypes.get_last_error()
            err_msg = {
                1409: "热键已被其他程序占用",
                87: "参数无效",
                5: "拒绝访问（无管理员权限？）",
            }.get(err, f"错误码({err})")
            logger.warning("[NativeHotkey] 注册失败: %s -> %s (err=%d: %s)",
                          action, sequence, err, err_msg)
        return bool(result)

    def unregisterHotkey(self, action: str):
        """注销热键"""
        hid = self._action_map.pop(action, None)
        if hid is not None and hid in self._registered:
            self._user32.UnregisterHotKey(None, hid)
            del self._registered[hid]
            logger.info("[NativeHotkey] 注销: %s (id=%d)", action, hid)

    def unregisterAll(self):
        """注销所有热键"""
        for hid in list(self._registered.keys()):
            self._user32.UnregisterHotKey(None, hid)
        self._registered.clear()
        self._action_map.clear()
        logger.info("[NativeHotkey] 全部热键已注销")

    def nativeEventFilter(self, eventType, message):
        """处理 Windows 原生事件

        注意：PySide6 要求返回 (bool, int) 元组，不能只返回 bool。
        第一个 bool：True=拦截消息, False=继续传递
        第二个 int：Windows LRESULT 值
        """
        try:
            # 用 __int__() 获取指针地址（兼容 PySide6 内部类型）
            addr = message.__int__()
            if addr == 0:
                return (False, 0)

            # 从内存地址读取 MSG 结构体
            # 参考 PySide6 官方 CSDN 教程：用 from_address 替代 ctypes.cast
            msg = ctypes.wintypes.MSG.from_address(addr)

            # WM_HOTKEY (0x0312) 的热键消息
            # Qt 文档：WM_HOTKEY 的 eventType 是 "windows_dispatcher_MSG"
            # 但为了兼容，我们检查 msg.message 而非 eventType
            if msg.message == WM_HOTKEY:
                hid = msg.wParam  # wParam = 热键 ID
                action = self._registered.get(hid)
                if action:
                    logger.info("[NativeHotkey] WM_HOTKEY: %s (id=%d)", action, hid)
                    self._callback(action)
                    return (True, 0)  # 已处理，不继续传递

        except Exception as e:
            logger.error("[NativeHotkey] nativeEventFilter 异常: %s", e, exc_info=True)

        # 未处理 → 返回 (False, 0) 让 Qt 继续处理该消息
        return (False, 0)
