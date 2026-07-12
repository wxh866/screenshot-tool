"""日志工具"""
import logging
import sys
from pathlib import Path


def _get_log_dir():
    """获取日志目录：优先写在EXE/项目目录下，避免写入用户home被拒绝"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 单文件模式：日志放在EXE旁边
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "logs"


def setupLogger(name: str = "ScreenshotTool", level: int = logging.DEBUG) -> logging.Logger:
    """配置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler（如多次import）
    if logger.handlers:
        return logger

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # 文件输出 — 写入失败不阻塞启动
    try:
        log_dir = _get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"

        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        pass  # 无文件系统写入权限时跳过，仅用控制台

    return logger


# 全局日志器
logger = setupLogger()
