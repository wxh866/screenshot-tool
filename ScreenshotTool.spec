# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 - 截图软件"""

import sys
from pathlib import Path

# 项目根目录 (spec文件同目录)
PROJECT_ROOT = Path(SPECPATH)  # SPECPATH 即 spec 文件所在目录

# ---- 收集QML文件 ----
qml_files = []
views_dir = PROJECT_ROOT / "views"
for qml_file in sorted(views_dir.glob("*.qml")):
    qml_files.append((str(qml_file), "views"))

# ---- 收集JSON配置 ----
json_datas = []

# data/config/*.json (单一配置源, 运行时可读写)
config_dir = PROJECT_ROOT / "data" / "config"
for json_file in sorted(config_dir.glob("*.json")):
    json_datas.append((str(json_file), "data/config"))

# themes/*.json
themes_dir = PROJECT_ROOT / "themes"
for json_file in sorted(themes_dir.glob("*.json")):
    json_datas.append((str(json_file), "themes"))

# ---- 隐藏导入 (动态加载的模块) ----
hidden_imports = [
    # 核心模块
    "core.event_bus",
    "core.config_manager",
    "core.undo_manager",
    "core.capture_service",
    "core.annotation_service",
    "core.history_manager",
    # 控制器
    "controllers.screenshot_controller",
    "controllers.editor_controller",
    "controllers.history_controller",
    # 数据模型
    "models.annotation",
    "models.screenshot",
    "models.tool_config",
    # 工具
    "engines.annotation.base",
    "engines.annotation.brush",
    "engines.annotation.line",
    "engines.annotation.rect",
    "engines.annotation.circle",
    "engines.annotation.arrow",
    "engines.annotation.text",
    "engines.annotation.mosaic",
    "engines.annotation.highlight",
    "engines.annotation.eraser",
    "engines.annotation.watermark",
    "engines.annotation.smart_select",
    "engines.annotation.polygon",
    # 截图引擎 (动态加载)
    "engines.capture.fullscreen",
    "engines.capture.region",
    "engines.capture.window",
    "engines.capture.scrolling",
    # 截图几何工具 (DPI/多屏/越界换算)
    "utils.capture_geometry",
    # 导出引擎 (动态加载)
    "engines.export.base",
    "engines.export.png_exporter",
    "engines.export.jpg_exporter",
    "engines.export.pdf_exporter",
    "engines.export.bmp_exporter",
    # 主题
    "themes.theme_manager",
    "themes.wcag_validator",
    # 工具
    "utils.logger",
    "utils.hotkey_manager",
    "platforms.native_hotkey",
    "utils.app_dir",
    "utils.image_utils",
    # PySide6 内部依赖
    "PySide6.QtNetwork",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtQuickControls2",  # QQuickStyle 依赖
    # PySide6 6.11.1 中 QtQmlModels 是 QtQml 内部模块，不需要单独导入
    # "PySide6.QtQmlModels",
    "PySide6.QtOpenGLWidgets",  # QML 渲染可能依赖
    # 第三方必备
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "numpy",
    "cv2",
    "keyboard",
    "pyautogui",
]

# ---- PyInstaller Analysis ----
a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=qml_files + json_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pandas",
        "scipy",
        "traitlets",
        "IPython",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ---- 过滤不需要的Qt模块缩减体积 ----
excluded_qt = [
    "QtWebEngine", "QtWebEngineCore", "QtWebEngineWidgets",
    "QtWebChannel",
    # NOTE: QtNetwork / QtQuickControls2 / QtQmlModels 均为 QML 引擎必需，不能排除
    "QtQuickTest",
    "QtMultimedia", "QtMultimediaWidgets",
    "QtSensors", "QtPositioning", "QtLocation",
    "QtSql", "QtTest", "QtXml", "QtXmlPatterns",
    "QtPrintSupport", "QtDesigner", "QtHelp",
    "QtBluetooth", "QtNfc", "QtSerialPort",
]

# 过滤二进制文件
binaries_filtered = []
for bin_info in a.binaries:
    path_lower = bin_info[0].lower()
    skip = False
    for excl in excluded_qt:
        if excl.lower() in path_lower:
            skip = True
            break
    if not skip:
        binaries_filtered.append(bin_info)

a.binaries = binaries_filtered

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ScreenshotTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # 后续可添加图标路径
)
