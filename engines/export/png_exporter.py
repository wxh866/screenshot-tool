"""PNG导出器"""
from PIL import Image
from engines.export.base import BaseExporter


class PNGExporter(BaseExporter):
    """PNG格式导出"""

    def export(self, image: Image.Image, path: str, **kwargs) -> str:
        """导出PNG格式"""
        image.save(path, "PNG", optimize=True)
        return path
