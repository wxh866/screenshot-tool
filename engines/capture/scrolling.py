"""滚动截图引擎 - ORB特征拼接（参考JamTools）"""
import time
import tempfile
from typing import Optional
import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QGuiApplication
from PIL import Image

from models.screenshot import ScreenshotData, CaptureMode
from utils.logger import logger
from utils.image_utils import pixmapToPil


class ScrollingCapture(QObject):
    """滚动截图 - 自动滚动+逐帧拼接"""

    captureProgress = Signal(int, int)   # current_frame, estimated_total
    captureFinished = Signal(object)     # ScreenshotData

    def __init__(self):
        super().__init__()
        self._frames = []
        self._is_capturing = False
        self._tryImportCV()

    def _tryImportCV(self):
        """尝试导入OpenCV"""
        try:
            import cv2
            self._has_cv = True
        except ImportError:
            self._has_cv = False
            logger.warning("OpenCV不可用，滚动截图功能受限")

    def capture(self) -> None:
        """启动滚动截图（异步模式）"""
        if not self._has_cv:
            logger.warning("滚动截图需要OpenCV支持")
            return None

        self._frames = []
        self._is_capturing = True

        # 截取第一帧
        first_frame = self._captureCurrentScreen()
        if first_frame:
            self._frames.append(first_frame)

        # 启动滚动循环
        self._scrollCount = 0
        self._maxScrolls = 20  # 最多20次滚动
        self._startScrollLoop()

    def _startScrollLoop(self):
        """开始滚动循环"""
        if not self._is_capturing or self._scrollCount >= self._maxScrolls:
            self._finishCapture()
            return

        # 模拟滚动
        self._simulateScroll()

        # 延迟截取下一帧
        QTimer.singleShot(500, self._captureNextFrame)

    def _captureCurrentScreen(self) -> Optional[Image.Image]:
        """截取当前屏幕"""
        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0)
        return pixmapToPil(pixmap)

    def _simulateScroll(self):
        """模拟鼠标滚动"""
        try:
            import pyautogui
            pyautogui.scroll(-3)  # 向下滚动3格
        except Exception as e:
            logger.warning("滚动模拟失败: %s", e)
            # 尝试keyboard库
            try:
                import keyboard
                keyboard.send('page_down')
            except Exception:
                logger.warning("键盘滚动也失败")

    def _captureNextFrame(self):
        """截取并拼接下一帧"""
        current = self._captureCurrentScreen()
        if not current:
            self._finishCapture()
            return

        if self._has_cv and len(self._frames) > 0:
            merged = self._stitchFrames(self._frames[-1], current)
            if merged:
                self._frames[-1] = merged
            else:
                # 拼接失败，检查是否到达底部
                if self._isSimilar(self._frames[-1], current):
                    logger.info("检测到滚动到底部")
                    self._finishCapture()
                    return
                self._frames.append(current)
        else:
            self._frames.append(current)

        self._scrollCount += 1
        self.captureProgress.emit(self._scrollCount, self._maxScrolls)

        # 继续滚动
        self._startScrollLoop()

    def _stitchFrames(self, img1: Image.Image, img2: Image.Image) -> Optional[Image.Image]:
        """使用ORB特征拼接两帧"""
        import cv2

        # 统一转 RGB（pixmapToPil 现返回 RGBA，4 通道无法做 RGB2BGR）
        cv1_arr = cv2.cvtColor(np.array(img1.convert("RGB")), cv2.COLOR_RGB2BGR)
        cv2_arr = cv2.cvtColor(np.array(img2.convert("RGB")), cv2.COLOR_RGB2BGR)

        # ORB特征检测
        orb = cv2.ORB_create(nfeatures=500)
        kp1, des1 = orb.detectAndCompute(cv1_arr, None)
        kp2, des2 = orb.detectAndCompute(cv2_arr, None)

        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return None

        # BFMatcher匹配
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        if len(matches) < 10:
            return None

        # 取好的匹配点
        good_matches = matches[:min(50, len(matches))]

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # 计算偏移
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is None:
            return None

        # 计算重叠区域
        dy = int(abs(M[1, 2]))
        if dy < 10:
            return None  # 偏移太小，可能没有滚动

        # 简单纵向拼接
        h1, w1 = cv1_arr.shape[:2]
        h2, w2 = cv2_arr.shape[:2]

        # 截取img2的非重叠部分
        new_part = cv2_arr[dy:, :w2]
        if new_part.shape[0] < 5:
            return None

        # 合并
        result = np.vstack([cv1_arr, new_part])
        return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))

    def _isSimilar(self, img1: Image.Image, img2: Image.Image) -> bool:
        """检查两帧是否相似（判断是否到达底部）"""
        arr1 = np.array(img1.convert("RGB").resize((100, 100)))
        arr2 = np.array(img2.convert("RGB").resize((100, 100)))

        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        mean_diff = np.mean(diff)

        return mean_diff < 5.0  # 平均像素差小于5认为相似

    def _finishCapture(self):
        """完成滚动截图"""
        self._is_capturing = False

        if len(self._frames) > 0:
            # 正常流程中 _captureNextFrame 会把拼接结果持续写回 _frames[-1]，
            # 故成功时长度恒为 1、_frames[-1] 即完整图。
            # 仅当某次 ORB 拼接失败走了 append 分支，_frames 才会 >1，
            # 此时应把所有原始帧按序纵向拼接（参考 JamTools），而不是只取首帧。
            if len(self._frames) == 1:
                result = self._frames[-1]
            else:
                result = self._vstack_frames(self._frames)

            with tempfile.NamedTemporaryFile(suffix=".png", prefix="scrolling_", delete=False) as tmp:
                temp_path = tmp.name
            result.save(temp_path)

            data = ScreenshotData(
                image_path=temp_path,
                capture_mode=CaptureMode.SCROLLING,
                width=result.width,
                height=result.height,
                timestamp=time.time()
            )

            self.captureFinished.emit(data)
            logger.info("滚动截图完成: %dx%d", result.width, result.height)

    def stopCapture(self):
        """手动停止滚动截图"""
        self._is_capturing = False

    def _vstack_frames(self, frames):
        """按捕获顺序纵向拼接多帧（ORB 拼接失败时的回退）。

        统一到最大宽度，透明背景，逐帧向下粘贴。
        """
        from PIL import Image
        frames = [f.convert("RGBA") for f in frames]
        max_w = max(f.width for f in frames)
        total_h = sum(f.height for f in frames)
        canvas = Image.new("RGBA", (max_w, total_h), (0, 0, 0, 0))
        y = 0
        for f in frames:
            canvas.paste(f, (0, y))
            y += f.height
        return canvas.convert("RGB")
