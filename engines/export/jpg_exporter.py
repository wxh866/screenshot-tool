"""JPG导出器"""
from PIL import Image
from engines.export.base import BaseExporter


class JPGExporter(BaseExporter):
    """JPG格式导出"""

    def export(self, image: Image.Image, path: str, quality: int = 95, **kwargs) -> str:
        """导出JPG格式"""
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        image.save(path, "JPEG", quality=quality)
        return path
