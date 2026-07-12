"""主题系统初始化"""
# ThemeManager依赖PySide6，单独导入
# WCAG验证器不依赖PySide6，可直接导入
from themes.wcag_validator import WCAGValidator, calc_contrast, check_contrast

__all__ = ['WCAGValidator', 'calc_contrast', 'check_contrast']

# PySide6可用时才导入ThemeManager
try:
    from themes.theme_manager import ThemeManager
    __all__.append('ThemeManager')
except ImportError:
    pass
