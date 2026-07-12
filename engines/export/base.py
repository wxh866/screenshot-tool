"""导出器基类"""
from abc import ABC, abstractmethod
from PIL import Image


class BaseExporter(ABC):
    """导出器基类"""

    @abstractmethod
    def export(self, image: Image.Image, path: str, **kwargs) -> str:
        """导出图像"""
        pass
