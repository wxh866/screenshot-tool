# 截图工具 2 (ScreenshotTool)

一个基于 **PySide6 + QML** 的离线截图与标注桌面工具，支持全屏 / 区域 / 窗口 / 滚动截图，以及矩形、椭圆、箭头、文字、马赛克、水印、智能选区等 12 种标注工具，内置撤销/重做、历史记录、主题切换与一键导出/复制到剪贴板。

## 特性

- **多种截图模式**：全屏、自定义区域、窗口、长图滚动拼接
- **12 种标注工具**：画笔、直线、矩形、椭圆、箭头、文字、马赛克、高亮、橡皮擦、水印、智能选区、多边形
- **编辑能力**：撤销 / 重做（Command 模式）、历史记录回放
- **导出与分享**：PNG / JPG / BMP / PDF 导出，直接复制到系统剪贴板（保留透明通道）
- **主题系统**：深色 / 浅色双主题，内置 WCAG 对比度校验
- **快捷键**：全局热键截图（Windows 原生注册）
- **离线优先**：纯本地运行，无网络依赖

## 技术栈

| 层 | 技术 |
| --- | --- |
| GUI | PySide6 (Qt Quick / QML, MVVM) |
| 图像处理 | Pillow, OpenCV (headless) |
| 事件 | Qt 信号槽 + 事件总线 (EventBus) |
| 配置 | JSON 文件 |
| 打包 | PyInstaller (onefile) |

## 目录结构

```
ScreenshotTool/
├── main.py                 # 应用主入口
├── requirements.txt        # Python 依赖
├── ScreenshotTool.spec     # PyInstaller 打包配置
├── controllers/            # 控制器（截图/编辑器/历史）
├── core/                   # 核心服务（截图/标注/配置/事件/撤销/历史）
├── engines/                # 引擎层
│   ├── annotation/         # 12 种标注工具实现
│   ├── capture/            # 截图引擎（全屏/区域/窗口/滚动）
│   └── export/             # 导出引擎（PNG/JPG/BMP/PDF）
├── models/                 # 数据模型
├── platforms/              # 平台相关（Windows 热键/Win32）
├── themes/                 # 主题 JSON + 主题管理 + WCAG 校验
├── utils/                  # 通用工具（日志/剪贴板/几何换算…）
├── views/                  # QML 视图（主界面/区域遮罩/编辑器/历史）
├── data/config/            # 默认配置源（app_config.json, hotkeys.json）
├── tests/                  # 单元测试套件
├── docs/                   # 设计/审查/测试/修复报告
└── .github/workflows/      # CI（pytest）
```

## 安装与运行

```bash
# 1. 安装依赖（建议虚拟环境）
pip install -r requirements.txt

# 2. 开发模式运行
python main.py

# 3. 运行测试
python run_tests.py
```

## 打包

```bash
pyinstaller ScreenshotTool.spec
# 产物：dist/ScreenshotTool.exe
```

## 许可证

[MIT](LICENSE)
