# 截图工具 Screenshot Tool

> 🚀 一款简洁高效的 Windows 桌面截图工具，支持深色/浅色双主题、多种截图模式与丰富标注功能。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightgrey.svg)]()

---

## ✨ 功能特性

| 模块 | 功能 |
|------|------|
| 📷 **截图模式** | 全屏截图、区域截图、窗口截图、滚动截图 |
| ✏️ **标注工具** | 画笔、直线、矩形、圆形、箭头、文字、马赛克、高亮、橡皮擦、水印 |
| 🎨 **双主题** | 深色/浅色一键切换，色彩对比度达 WCAG AA 标准 |
| 📌 **工具栏** | 支持悬浮与固定两种模式，自适应布局 |
| 📋 **历史记录** | 截图历史面板，快速回溯与复用 |
| 💾 **一键操作** | 保存到本地、复制到剪贴板、自定义保存路径 |

---

## 📸 界面预览

### 深色主题
深色主题以 `#0F0F1A` 为底色，降低长时间使用的视觉疲劳。

### 浅色主题
浅色主题以 `#EEF0F4` 为底色，适合白天办公环境。

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Shift + S` | 触发截图 |
| `Ctrl + C` | 复制到剪贴板 |
| `Ctrl + S` | 保存截图 |
| `Ctrl + Z` | 撤销标注 |
| `Esc` | 取消截图 / 退出 |

---

## 🔧 安装与运行

### 环境要求

- Windows 10 或更高版本
- Python 3.8 或更高版本

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/wxh866/-.git
cd -

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行截图工具
python screenshot_tool.py
```

或者双击 `run.bat` 一键启动。

### 依赖项

| 库 | 版本 | 用途 |
|----|------|------|
| Pillow | >=10.0.0 | 图像采集、编辑、保存 |
| keyboard | >=0.13.5 | 全局热键监听（可选） |

---

## 📁 项目结构

```
截图工具/
├── screenshot_tool.py          # 主程序入口（约2900行）
├── theme_colors.py             # 统一主题色彩管理模块
├── requirements.txt            # Python 依赖清单
├── run.bat                     # Windows 一键启动脚本
├── settings.json               # 用户配置文件
├── dist/                       # 打包输出目录
├── design-spec.md              # UI 设计规范文档
├── theme-system.md             # 主题色彩体系说明
├── design-showcase.html        # 设计原型展示页
├── screenshot-ui-prototype.html # UI 交互原型
├── LICENSE                     # 开源许可证
├── CHANGELOG.md                # 版本更新记录
└── README.md                   # 本文件
```

---

## 🎨 主题色彩体系

项目采用**统一主题色彩管理系统**，所有颜色由 `theme_colors.py` 中的 `T` 类集中管理：

```python
from theme_colors import T

# 深色/浅色自动切换
T.set_theme('dark')   # 或 'light'
bg = T.BG2            # 自动返回当前主题对应的颜色
accent = T.ACCENT     # 强调色
```

颜色令牌分三层：
- **L1 基础色**：背景层次（BG0～BG4）、文字（TXT0～TXT3）、边框（BD/BD2）
- **L2 语义色**：ACCENT、RED、GREEN、ORANGE
- **L3 标注色板**：12 种固定标注颜色，双主题共用

详见 [`theme-system.md`](theme-system.md)。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。请参考 [`CONTRIBUTING.md`](CONTRIBUTING.md) 了解贡献流程。

---

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
