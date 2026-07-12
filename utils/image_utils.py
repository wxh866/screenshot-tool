"""图像处理工具函数"""
import numpy as np
from PIL import Image
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QSize


def pilToPixmap(image: Image.Image) -> QPixmap:
    """Pillow Image转QPixmap (兼容新版PySide6)"""
    # 统一转RGBA
    if image.mode not in ("RGBA", "RGB"):
        image = image.convert("RGBA")

    data = np.array(image).copy()  # copy确保数据独立
    h, w = data.shape[:2]

    if image.mode == "RGBA" or data.shape[2] == 4:
        qimage = QImage(data.tobytes(), w, h, w * 4, QImage.Format_RGBA8888)
    else:
        qimage = QImage(data.tobytes(), w, h, w * 3, QImage.Format_RGB888)

    return QPixmap.fromImage(qimage)


def pixmapToPil(pixmap: QPixmap) -> Image.Image:
    """QPixmap转Pillow Image (兼容PySide6.6+)"""
    qimage = pixmap.toImage()

    # 统一转RGBA8888格式
    if qimage.format() != QImage.Format_RGBA8888:
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)

    width = qimage.width()
    height = qimage.height()
    byte_count = width * height * 4

    # 使用constBits (返回bytes对象, 兼容新版PySide6)
    try:
        ptr = qimage.constBits()
        if isinstance(ptr, memoryview):
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 4)
        elif isinstance(ptr, bytes):
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 4)
        else:
            # 兜底: 使用QImage.bits() + 计算bytes
            ptr = qimage.bits()
            if hasattr(ptr, 'setsize'):
                ptr.setsize(byte_count)
            arr = np.array(ptr, copy=True).reshape(height, width, 4)
    except Exception:
        # 最终兜底: 通过QPixmap.save到BytesIO
        import io
        buf = io.BytesIO()
        pixmap.save(buf, "PNG")
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    # 保留 alpha 通道：之前 arr[..., :3] 会丢弃透明信息，
    # 导致窗口/区域截图（带圆角或透明叠加）被强制涂成黑底。
    return Image.fromarray(arr.copy(), "RGBA")


def createThumbnail(image: Image.Image, size: tuple = (200, 200)) -> Image.Image:
    """创建缩略图"""
    thumb = image.copy()
    thumb.thumbnail(size, Image.LANCZOS)
    return thumb


def getFont(size: int = 20):
    """获取字体（离线回退链）"""
    from PIL import ImageFont
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",   # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
        "C:/Windows/Fonts/arial.ttf",   # Arial
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()
