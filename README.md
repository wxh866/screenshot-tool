# 📸 截图工具 (ScreenshotTool)

> 轻量、离线、功能齐全的 Windows 截图 & 标注工具 —— 下载即用，无需安装。

## 立即下载

👉 **[点击下载 ScreenshotTool.exe](https://github.com/wxh866/screenshot-tool/releases/latest)**

下载后双击 `ScreenshotTool.exe` 即可使用，无需安装 Python 或任何依赖。

> 文件约 120MB（包含完整运行环境），首次启动可能需要几秒。

---

## 能做什么

### 截图模式

| 模式 | 说明 |
|------|------|
| 🖥 全屏截图 | 一键截取整个屏幕 |
| ✂️ 区域截图 | 拖拽选取任意区域 |
| 🪟 窗口截图 | 自动识别并截取窗口 |
| 📜 滚动截图 | 长网页 / 长文档滚动拼接 |

### 标注工具（12 种）

画笔 · 直线 · 矩形 · 椭圆 · 箭头 · **文字** · **马赛克** · 高亮 · 橡皮擦 · **水印** · 智能选区 · 多边形

### 编辑操作

- ↩️ **撤销 / 重做** — 无限步，不怕手滑
- 📋 **历史记录** — 随时回放到任意步骤
- 🖼 **导出格式** — PNG / JPG / BMP / PDF
- 📋 **复制到剪贴板** — 一键粘贴到微信/QQ/文档

### 其他亮点

- 🌓 **深色 / 浅色主题** — 白天夜晚都舒适
- ⌨️ **全局快捷键** — 一键唤醒截图
- 🔒 **离线运行** — 不联网，不传数据
- ⚖️ **MIT 开源** — 免费使用，源码可见

---

## 用法一览

```
默认快捷键:
  Ctrl+Shift+X  →  区域截图（最常用）
  Ctrl+Shift+C  →  全屏截图
  Ctrl+Shift+W  →  窗口截图
  
截图后编辑:
  鼠标点击拖拽  →  绘制标注
  Ctrl+Z       →  撤销
  Ctrl+Shift+Z →  重做
  Ctrl+S       →  保存到文件
  Ctrl+C       →  复制到剪贴板
  Esc          →  退出编辑器
```

---

## 系统要求

- Windows 10 / 11（64 位）
- 无需额外安装任何软件

---

## 开发者

<details>
<summary>从源码运行</summary>

```bash
pip install -r requirements.txt
python main.py
```

**技术栈**: PySide6 + QML · Pillow · OpenCV · PyInstaller

**目录结构**: `core/` 核心 · `controllers/` 控制器 · `engines/` 引擎 · `models/` 模型 · `views/` QML 视图
</details>

---

## 许可证

[MIT](LICENSE)
