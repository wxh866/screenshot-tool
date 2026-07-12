"""PDF导出器"""
from PIL import Image
from engines.export.base import BaseExporter


class PDFExporter(BaseExporter):
    """PDF格式导出"""

    def export(self, image: Image.Image, path: str, **kwargs) -> str:
        """导出PDF格式"""
        rgb_image = image.convert("RGB")
        rgb_image.save(path, "PDF")
        return path
