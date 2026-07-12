"""应用数据目录 - 统一获取可持久化的数据目录"""
import sys
from pathlib import Path


def _get_app_data_dir() -> Path:
    """获取应用数据目录（兼容开发环境和 PyInstaller onefile 模式）"""
    if getattr(sys, 'frozen', False):
        # onefile 模式下，持久化数据放在EXE旁边
        base = Path(sys.executable).parent
    else:
        # 开发模式：放在项目根目录
        base = Path(__file__).parent.parent
    return base / "data"


def get_data_dir() -> Path:
    """返回已创建的应用数据目录"""
    d = _get_app_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d
