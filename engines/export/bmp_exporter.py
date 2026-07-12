"""BMP导出器"""
from PIL import Image
from engines.export.base import BaseExporter


class BMPExporter(BaseExporter):
    """BMP格式导出"""

    def export(self, image: Image.Image, path: str, **kwargs) -> str:
        """导出BMP格式"""
        image.save(path, "BMP")
        return path
