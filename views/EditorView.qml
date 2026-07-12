// 截图编辑视图 — Canvas交互式标注编辑器
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: editorWindow
    visible: true
    flags: Qt.Window | Qt.WindowCloseButtonHint |
           Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
    title: "截图编辑" + (imagePath ? " - " + imagePath.split('/').pop() : "")

    property string imagePath: ""
    property int imageWidth: 0
    property int imageHeight: 0
    property string currentTool: "brush"
    property string toolColor: "#FF6B35"
    property int toolWidth: 7
    property int toolOpacity: 255
    property int toolMinWidth: 1
    property int toolMaxWidth: 30
    property bool canUndo: false
    property bool canRedo: false

    // 主题系统 — 从ThemeManager动态绑定，支持深色/浅色切换
    property var theme: ThemeManager ? ThemeManager.getTheme() : ({})
    property bool isDark: ThemeManager ? ThemeManager.isDark() : true

    property color bgApp: theme.background ? theme.background.app : "#141422"
    property color bgCard: theme.background ? theme.background.card : "#1e1e32"
    property color bgToolbar: theme.background ? theme.background.elevated : "#282844"
    property color bgSidebar: theme.background ? theme.background.card : "#1e1e32"
    property color txtPrimary: theme.text ? theme.text.primary : "#f0f0f8"
    property color txtSecondary: theme.text ? theme.text.secondary : "#b0b0c8"
    property color accentColor: theme.accent ? theme.accent.primary : "#4a8cff"
    property color borderColor: theme.border ? theme.border.default : "#2a2a44"
    property color dangerColor: theme.semantic ? theme.semantic.error : "#e05555"
    property color successColor: theme.semantic ? theme.semantic.success : "#4caf84"

    // 主题化 hover 颜色
    property color hoverColor: isDark ? "#333358" : "#eef1f6"
    property color hoverSaveColor: isDark ? "#2a5a3a" : "#d6f0e2"
    property color hoverDangerColor: isDark ? "#5a2a2a" : "#fde8e8"
    property color hoverClearColor: isDark ? "#3a1a1a" : "#fde8e8"
    property color dangerBorderColor: isDark ? "#5a2a2a" : "#f0c0c0"

    Connections {
        target: ThemeManager
        function onThemeChanged(name) {
            theme = ThemeManager.getTheme()
            isDark = ThemeManager.isDark()
            // 强制重绘所有Canvas
            checkerBg.requestPaint()
            annotationCanvas.requestPaint()
        }
    }

    // Toast
    property string toastMsg: ""
    property bool toastOn: false
    property string toastKind: "info"

    function showToast(msg, kind) {
        toastMsg = msg; toastKind = kind || "info"; toastOn = true
        toastTimer.start()
    }

    Timer {
        id: toastTimer
        interval: 2200
        onTriggered: toastOn = false
    }

    width: Math.min(imageWidth + 260, Screen.width * 0.9)
    height: Math.min(imageHeight + 110, Screen.height * 0.9)
    color: bgApp

    // ============ 键盘快捷键 ============
    // 用 Shortcut 替代 Keys.onPressed（更可靠，不受焦点影响）
    Shortcut { sequence: "Ctrl+Z";
        onActivated: { console.log("[EditorView] Ctrl+Z undo"); EditorController.undo() } }
    Shortcut { sequence: "Ctrl+Shift+Z";
        onActivated: { console.log("[EditorView] Ctrl+Shift+Z redo"); EditorController.redo() } }
    Shortcut { sequence: "Ctrl+S";
        onActivated: { console.log("[EditorView] Ctrl+S save"); doSave() } }
    Shortcut { sequence: "Ctrl+C";
        onActivated: { console.log("[EditorView] Ctrl+C copy"); doCopy() } }
    Shortcut { sequence: "Escape";
        onActivated: { console.log("[EditorView] Escape close"); if (!textInputDialog.visible) editorWindow.close() } }

    // ============ 顶部工具栏 ============
    header: Rectangle {
        color: bgToolbar
        height: 44
        border.color: borderColor

        // 左侧工具按钮组（居左，窄窗口下受限不覆盖右侧）
        RowLayout {
            id: leftTools
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, parent.width - rightActions.width - 16)
            clip: true
            spacing: 2

            // 工具按钮组
            Repeater {
                model: [
                    { text: "画笔",   tool: "brush",        color: "#FF6B35" },
                    { text: "直线",   tool: "line",         color: "#FF3B30" },
                    { text: "矩形",   tool: "rect",         color: "#007AFF" },
                    { text: "圆形",   tool: "circle",       color: "#007AFF" },
                    { text: "箭头",   tool: "arrow",        color: "#FF3B30" },
                    { text: "文字",   tool: "text",         color: "#FF3B30" },
                    { text: "马赛克", tool: "mosaic",       color: "#aaaaaa" },
                    { text: "高亮",   tool: "highlight",    color: "#FFCC02" },
                    { text: "橡皮擦", tool: "eraser",       color: "#ffffff" },
                    { text: "水印",   tool: "watermark",    color: "#888888" },
                    { text: "选区",   tool: "smart_select", color: "#4a8cff" },
                    { text: "多边形", tool: "polygon",      color: "#FF3B30" }
                ]
                ToolButton {
                    id: btn
                    property string toolId: modelData.tool
                    property string toolColorHint: modelData.color

                    implicitWidth: 40
                    implicitHeight: 34

                    background: Rectangle {
                        color: currentTool === modelData.tool ? accentColor :
                               (parent.hovered ? hoverColor : "transparent")
                        radius: 4
                        border.color: currentTool === modelData.tool ?
                                      Qt.lighter(accentColor, 1.3) : "transparent"
                        border.width: 1
                    }

                    contentItem: Text {
                        text: modelData.text
                        color: currentTool === modelData.tool ? "#FFFFFF" : txtPrimary
                        font.pixelSize: 11
                        font.family: "Microsoft YaHei"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    ToolTip {
                        text: modelData.text + " (" + modelData.tool + ")"
                        visible: parent.hovered
                        delay: 500
                    }

                    onClicked: {
                        EditorController.selectTool(modelData.tool)
                        currentTool = modelData.tool
                        toolColor = modelData.color
                        // 读取工具宽度范围并限制当前值
                        var cfg = JSON.parse(EditorController.getToolMinWidth())
                        toolMinWidth = cfg.min
                        toolMaxWidth = cfg.max
                        toolWidth = Math.round((cfg.min + cfg.max) / 3)
                        EditorController.setWidth(toolWidth)
                    }
                }
            }

            // 分隔线
            Rectangle { width: 1; height: 24; color: borderColor; Layout.alignment: Qt.AlignVCenter }

            // 操作按钮
            ToolButton {
                implicitWidth: 40
                implicitHeight: 34
                enabled: canUndo
                opacity: canUndo ? 1.0 : 0.4

                background: Rectangle {
                    color: parent.hovered && parent.enabled ? hoverColor : "transparent"
                    radius: 4
                }
                contentItem: Text {
                    text: "↩"
                    color: parent.enabled ? txtPrimary : txtSecondary
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                ToolTip { text: "撤销 (Ctrl+Z)"; visible: parent.hovered }
                onClicked: EditorController.undo()
            }

            ToolButton {
                implicitWidth: 40
                implicitHeight: 34
                enabled: canRedo
                opacity: canRedo ? 1.0 : 0.4

                background: Rectangle {
                    color: parent.hovered && parent.enabled ? hoverColor : "transparent"
                    radius: 4
                }
                contentItem: Text {
                    text: "↪"
                    color: parent.enabled ? txtPrimary : txtSecondary
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                ToolTip { text: "重做 (Ctrl+Shift+Z)"; visible: parent.hovered }
                onClicked: EditorController.redo()
            }
        }

        // 右侧保存/复制/关闭（固定居右，优先保留关闭）
        RowLayout {
            id: rightActions
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            z: 10  // 确保在最上层

            ToolButton {
                implicitWidth: 40
                implicitHeight: 34
                background: Rectangle {
                    color: parent.hovered ? hoverColor : "transparent"; radius: 4
                }
                contentItem: Text {
                    text: "保存"
                    color: successColor; font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                ToolTip { text: "保存文件 (Ctrl+S)"; visible: parent.hovered }
                onClicked: doSave()
            }
            ToolButton {
                implicitWidth: 40
                implicitHeight: 34
                background: Rectangle {
                    color: parent.hovered ? hoverColor : "transparent"; radius: 4
                }
                contentItem: Text {
                    text: "复制"
                    color: txtPrimary; font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                ToolTip { text: "复制到剪贴板 (Ctrl+C)"; visible: parent.hovered }
                onClicked: doCopy()
            }
            ToolButton {
                implicitWidth: 40
                implicitHeight: 34
                background: Rectangle {
                    color: parent.hovered ? hoverColor : "transparent"; radius: 4
                }
                contentItem: Text {
                    text: "关闭"
                    color: dangerColor; font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                ToolTip { text: "关闭编辑器 (Esc)"; visible: parent.hovered }
                onClicked: editorWindow.close()
            }
        }
    }

    // ============ 主体布局: 图片区 + 侧边栏 ============
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // — 图片编辑区 —
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flickable {
                id: imageFlickable
                anchors.fill: parent
                anchors.margins: 10
                clip: true
                contentWidth: imageContainer.width
                contentHeight: imageContainer.height
                boundsBehavior: Flickable.StopAtBounds

                Item {
                    id: imageContainer
                    width: Math.max(imageWidth + 4, imageFlickable.width - 20)
                    height: Math.max(imageHeight + 4, imageFlickable.height - 20)

                    // 棋盘格背景
                    Canvas {
                        id: checkerBg
                        anchors.centerIn: parent
                        width: annotationCanvas.width
                        height: annotationCanvas.height

                        onPaint: {
                            var ctx = getContext("2d")
                            var size = 12
                            for (var y = 0; y < height; y += size) {
                                for (var x = 0; x < width; x += size) {
                                    ctx.fillStyle = ((Math.floor(x/size) + Math.floor(y/size)) % 2 === 0)
                                        ? (isDark ? "#2a2a42" : "#e0e3ea")
                                        : (isDark ? "#222238" : "#eceef4")
                                    ctx.fillRect(x, y, size, size)
                                }
                            }
                        }
                    }

                    // 底图
                    Image {
                        id: imagePreview
                        anchors.centerIn: parent
                        source: imagePath ? "file:///" + imagePath : ""
                        width: imageWidth
                        height: imageHeight
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        cache: false
                        // 破坏性操作（马赛克/橡皮擦/水印）会更新到底图，
                        // 通过时间戳参数强制刷新，避免 Qt 图片缓存导致看不到变化
                        property int reloadToken: 0
                    }

                    // 标注Canvas覆盖层
                    Canvas {
                        id: annotationCanvas
                        anchors.centerIn: parent
                        width: imageWidth
                        height: imageHeight
                        z: 10

                        property var previewData: null
                        property var annotationsData: []

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            // 1. 绘制所有已完成的标注
                            if (annotationsData.length > 0) {
                                for (var i = 0; i < annotationsData.length; i++) {
                                    drawAnnotation(ctx, annotationsData[i])
                                }
                            }

                            // 2. 绘制当前预览（正在绘制的标注）
                            if (previewData && previewData.points && previewData.points.length > 0) {
                                drawAnnotation(ctx, previewData, true)
                            }
                        }

                        // ===== 工具绘制函数（统一入口：preview=true为半透明预览） =====

                        function hexToRGBA(hex, alpha) {
                            hex = hex.replace("#", "")
                            if (hex.length === 3) {
                                hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2]
                            }
                            var r = parseInt(hex.substring(0,2), 16)
                            var g = parseInt(hex.substring(2,4), 16)
                            var b = parseInt(hex.substring(4,6), 16)
                            return "rgba(" + r + "," + g + "," + b + "," + (alpha/255).toFixed(2) + ")"
                        }

                        function drawAnnotation(ctx, ann, isPreview) {
                            var color = hexToRGBA(ann.color, ann.opacity || 255)
                            var pts = ann.points
                            var w = ann.width || 3

                            // 预览模式下降低不透明度
                            if (isPreview) {
                                color = hexToRGBA(ann.color, Math.round((ann.opacity || 128) * 0.6))
                            }

                            ctx.save()
                            switch (ann.tool_type) {

                            // ===== 画笔 =====
                            case "brush":
                                if (pts.length >= 2) {
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(pts[0][0], pts[0][1])
                                    for (var bi = 1; bi < pts.length; bi++) {
                                        ctx.lineTo(pts[bi][0], pts[bi][1])
                                    }
                                    ctx.stroke()
                                }
                                break

                            // ===== 直线 =====
                            case "line":
                                if (pts.length >= 2) {
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.lineCap = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(pts[0][0], pts[0][1])
                                    ctx.lineTo(pts[pts.length-1][0], pts[pts.length-1][1])
                                    ctx.stroke()
                                }
                                break

                            // ===== 矩形 =====
                            case "rect":
                                if (pts.length >= 2) {
                                    var rx = Math.min(pts[0][0], pts[pts.length-1][0])
                                    var ry = Math.min(pts[0][1], pts[pts.length-1][1])
                                    var rw = Math.abs(pts[pts.length-1][0] - pts[0][0])
                                    var rh = Math.abs(pts[pts.length-1][1] - pts[0][1])
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.strokeRect(rx, ry, rw, rh)
                                }
                                break

                            // ===== 圆形 =====
                            case "circle":
                                if (pts.length >= 2) {
                                    var cx = (pts[0][0] + pts[pts.length-1][0]) / 2
                                    var cy = (pts[0][1] + pts[pts.length-1][1]) / 2
                                    var crx = Math.abs(pts[pts.length-1][0] - pts[0][0]) / 2
                                    var cry = Math.abs(pts[pts.length-1][1] - pts[0][1]) / 2
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.beginPath()
                                    ctx.ellipse(cx, cy, crx, cry, 0, 0, Math.PI * 2)
                                    ctx.stroke()
                                }
                                break

                            // ===== 箭头 =====
                            case "arrow":
                                if (pts.length >= 2) {
                                    drawArrow(ctx,
                                        pts[0][0], pts[0][1],
                                        pts[pts.length-1][0], pts[pts.length-1][1],
                                        color, w)
                                }
                                break

                            // ===== 文字 =====
                            case "text":
                                if (pts.length >= 1 && !isPreview) {
                                    var txt = ann.properties ? (ann.properties.text || "文字") : "文字"
                                    var fs = ann.width || 20
                                    var bold = ann.properties ? (ann.properties.bold || false) : false
                                    var useBg = ann.properties ? (ann.properties.background || false) : false
                                    ctx.fillStyle = ann.properties ?
                                        (ann.properties.text_color || color) : color
                                    ctx.font = (bold ? "bold " : "") + fs + "px 'Microsoft YaHei', sans-serif"
                                    ctx.textBaseline = "top"
                                    var lines = String(txt).split("\n")
                                    var lineH = fs * 1.3
                                    if (useBg) {
                                        // 半透明背景，保证任意底色可读（参考 Flameshot）
                                        ctx.save()
                                        var maxW = 0
                                        for (var li = 0; li < lines.length; li++) {
                                            var w = ctx.measureText(lines[li]).width
                                            if (w > maxW) maxW = w
                                        }
                                        ctx.fillStyle = "rgba(0,0,0,0.45)"
                                        ctx.fillRect(pts[0][0] - 4, pts[0][1] - 2,
                                                     maxW + 8, lines.length * lineH + 4)
                                        ctx.fillStyle = ann.properties ?
                                            (ann.properties.text_color || color) : color
                                        ctx.restore()
                                    }
                                    for (var lj = 0; lj < lines.length; lj++) {
                                        ctx.fillText(lines[lj], pts[0][0], pts[0][1] + lj * lineH)
                                    }
                                }
                                break

                            // ===== 马赛克（矩形区域网格） =====
                            case "mosaic":
                                if (pts.length >= 2) {
                                    var mx = Math.min(pts[0][0], pts[pts.length-1][0])
                                    var my = Math.min(pts[0][1], pts[pts.length-1][1])
                                    var mw = Math.abs(pts[pts.length-1][0] - pts[0][0])
                                    var mh = Math.abs(pts[pts.length-1][1] - pts[0][1])
                                    if (mw > 0 && mh > 0) {
                                        ctx.save()
                                        // 矩形边框
                                        ctx.strokeStyle = hexToRGBA("#888888", isPreview ? 180 : 220)
                                        ctx.lineWidth = 2
                                        ctx.setLineDash(isPreview ? [5, 5] : [])
                                        ctx.strokeRect(mx, my, mw, mh)
                                        ctx.setLineDash([])

                                        // 马赛克网格填充（预览效果）
                                        var bs = isPreview ? 8 : 8
                                        ctx.fillStyle = hexToRGBA("#888888", isPreview ? 30 : 50)
                                        for (var mby = my; mby < my + mh; mby += bs) {
                                            for (var mbx = mx; mbx < mx + mw; mbx += bs) {
                                                ctx.fillRect(mbx, mby, bs/2, bs/2)
                                                mbx += bs/2
                                            }
                                        }

                                        // 对角线装饰线
                                        ctx.strokeStyle = hexToRGBA("#aaaaaa", isPreview ? 40 : 60)
                                        ctx.lineWidth = 1
                                        ctx.beginPath()
                                        ctx.moveTo(mx, my); ctx.lineTo(mx + mw, my + mh)
                                        ctx.moveTo(mx + mw, my); ctx.lineTo(mx, my + mh)
                                        ctx.stroke()
                                        ctx.restore()
                                    }
                                }
                                break

                            // ===== 高亮（半透明矩形） =====
                            case "highlight":
                                if (pts.length >= 2) {
                                    var hx = Math.min(pts[0][0], pts[pts.length-1][0])
                                    var hy = Math.min(pts[0][1], pts[pts.length-1][1])
                                    var hw = Math.abs(pts[pts.length-1][0] - pts[0][0])
                                    var hh = Math.abs(pts[pts.length-1][1] - pts[0][1])
                                    ctx.fillStyle = hexToRGBA(ann.color, Math.min(ann.opacity || 255, 80))
                                    ctx.fillRect(hx, hy, hw, hh)
                                }
                                break

                            // ===== 橡皮擦（圆形轮廓） =====
                            case "eraser":
                                for (var ei = 0; ei < pts.length; ei++) {
                                    // 外圈（指示擦除范围）
                                    ctx.strokeStyle = "rgba(255,255,255,0.8)"
                                    ctx.lineWidth = 1.5
                                    ctx.beginPath()
                                    ctx.arc(pts[ei][0], pts[ei][1], w, 0, Math.PI * 2)
                                    ctx.stroke()
                                    // 内圈（半透明）
                                    ctx.fillStyle = "rgba(255,255,255,0.15)"
                                    ctx.beginPath()
                                    ctx.arc(pts[ei][0], pts[ei][1], w - 1, 0, Math.PI * 2)
                                    ctx.fill()
                                }
                                break

                            // ===== 水印（平铺文字，实时预览即真实效果） =====
                            case "watermark":
                                drawWatermark(ctx, ann, width, height)
                                break

                            // ===== 智能选区（虚线矩形） =====
                            case "smart_select":
                                if (pts.length >= 2) {
                                    var sx = Math.min(pts[0][0], pts[pts.length-1][0])
                                    var sy = Math.min(pts[0][1], pts[pts.length-1][1])
                                    var sw = Math.abs(pts[pts.length-1][0] - pts[0][0])
                                    var sh = Math.abs(pts[pts.length-1][1] - pts[0][1])
                                    ctx.save()
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.setLineDash([8, 4])
                                    ctx.strokeRect(sx, sy, sw, sh)
                                    ctx.setLineDash([])
                                    // 四个角标
                                    var ch = 12
                                    ctx.fillStyle = hexToRGBA(ann.color, 200)
                                    // 左上
                                    ctx.fillRect(sx-ch/2, sy-ch/2, ch, ch)
                                    // 右上
                                    ctx.fillRect(sx+sw-ch/2, sy-ch/2, ch, ch)
                                    // 左下
                                    ctx.fillRect(sx-ch/2, sy+sh-ch/2, ch, ch)
                                    // 右下
                                    ctx.fillRect(sx+sw-ch/2, sy+sh-ch/2, ch, ch)
                                    ctx.restore()
                                }
                                break

                            // ===== 多边形 =====
                            case "polygon":
                                if (pts.length >= 2) {
                                    ctx.strokeStyle = color
                                    ctx.lineWidth = w
                                    ctx.lineJoin = "round"
                                    ctx.beginPath()
                                    ctx.moveTo(pts[0][0], pts[0][1])
                                    for (var pi = 1; pi < pts.length; pi++) {
                                        ctx.lineTo(pts[pi][0], pts[pi][1])
                                    }
                                    if (pts.length >= 3 && !isPreview) {
                                        ctx.closePath()
                                    }
                                    ctx.stroke()

                                    // 顶点标记小圆点
                                    ctx.fillStyle = color
                                    for (var pj = 0; pj < pts.length; pj++) {
                                        ctx.beginPath()
                                        ctx.arc(pts[pj][0], pts[pj][1], 3, 0, Math.PI * 2)
                                        ctx.fill()
                                    }

                                    // 预览模式：连接首尾的虚线
                                    if (isPreview && pts.length >= 3) {
                                        ctx.save()
                                        ctx.strokeStyle = hexToRGBA(ann.color, 100)
                                        ctx.lineWidth = 1
                                        ctx.setLineDash([5, 5])
                                        ctx.beginPath()
                                        ctx.moveTo(pts[pts.length-1][0], pts[pts.length-1][1])
                                        ctx.lineTo(pts[0][0], pts[0][1])
                                        ctx.stroke()
                                        ctx.setLineDash([])
                                        ctx.restore()
                                    }
                                }
                                break
                            }
                            ctx.restore()
                        }

                        // ===== 辅助绘图函数 =====

                        function drawArrow(ctx, x1, y1, x2, y2, color, w) {
                            ctx.save()
                            ctx.strokeStyle = color
                            ctx.lineWidth = w
                            ctx.lineCap = "round"

                            // 参考 Flameshot/ShareX：主线段终点缩进箭头底边，
                            // 避免 round cap 的半圆突出到三角头之外。
                            var angle = Math.atan2(y2 - y1, x2 - x1)
                            var arrowSize = Math.max(w * 5, 12)
                            var dx = x2 - x1
                            var dy = y2 - y1
                            var len = Math.sqrt(dx * dx + dy * dy)
                            var lineX2 = x2
                            var lineY2 = y2
                            if (len > arrowSize) {
                                lineX2 = x2 - arrowSize * Math.cos(angle)
                                lineY2 = y2 - arrowSize * Math.sin(angle)
                            }

                            // 主线条
                            ctx.beginPath()
                            ctx.moveTo(x1, y1)
                            ctx.lineTo(lineX2, lineY2)
                            ctx.stroke()

                            // 箭头头部
                            ctx.fillStyle = color
                            ctx.beginPath()
                            ctx.moveTo(x2, y2)
                            ctx.lineTo(
                                x2 - arrowSize * Math.cos(angle - 0.4),
                                y2 - arrowSize * Math.sin(angle - 0.4)
                            )
                            ctx.lineTo(
                                x2 - arrowSize * Math.cos(angle + 0.4),
                                y2 - arrowSize * Math.sin(angle + 0.4)
                            )
                            ctx.closePath()
                            ctx.fill()
                            ctx.restore()
                        }

                        function drawWatermark(ctx, ann, canvasW, canvasH) {
                            var txt = ann.properties ? (ann.properties.text || "水印") : "水印"
                            var fontSize = ann.width || 52
                            var wmColor = hexToRGBA(ann.color, Math.min(ann.opacity || 255, 60))
                            var mode = ann.properties ? (ann.properties.mode || "tile") : "tile"
                            var rotation = ann.properties ? (ann.properties.rotation || 28) : 28
                            var rad = rotation * Math.PI / 180

                            ctx.save()
                            ctx.fillStyle = wmColor
                            ctx.font = fontSize + "px 'Microsoft YaHei', sans-serif"
                            ctx.textBaseline = "top"

                            if (mode === "center") {
                                ctx.translate(canvasW/2, canvasH/2)
                                ctx.rotate(rad)
                                ctx.textAlign = "center"
                                ctx.fillText(txt, 1, 1)
                                ctx.fillText(txt, 0, 0)
                            } else {
                                var stepX = fontSize * 4
                                var stepY = fontSize * 3
                                ctx.textAlign = "left"
                                for (var wy = 0; wy < canvasH + stepY; wy += stepY) {
                                    for (var wx = 0; wx < canvasW + stepX; wx += stepX) {
                                        ctx.save()
                                        ctx.translate(wx, wy)
                                        ctx.rotate(rad)
                                        ctx.fillText(txt, 1, 1)
                                        ctx.restore()
                                    }
                                }
                            }
                            ctx.restore()
                        }
                    }

                        // 鼠标事件捕获层
                        MouseArea {
                            id: canvasMouseArea
                            anchors.fill: annotationCanvas

                            hoverEnabled: true
                            // 不同工具用不同光标
                            cursorShape: {
                                switch (currentTool) {
                                case "text": return Qt.IBeamCursor
                                case "eraser": return Qt.BlankCursor
                                default: return Qt.CrossCursor
                                }
                            }

                            property int lastX: 0
                            property int lastY: 0
                            property var lastPressTime: 0

                            onPressed: function(mouse) {
                                lastPressTime = Date.now()

                                // 文字工具: 点击后弹出模态输入对话框
                                if (currentTool === "text") {
                                    textInputDialog.mouseX = mouse.x
                                    textInputDialog.mouseY = mouse.y
                                    textInputDialog.open()
                                    return
                                }

                                lastX = mouse.x; lastY = mouse.y
                                EditorController.mousePress(mouse.x, mouse.y)
                            }
                            onDoubleClicked: function(mouse) {
                                // 多边形工具: 双击闭合（参考 Flameshot 多边形工具）
                                if (currentTool === "polygon") {
                                    EditorController.finishPolygon(mouse.x, mouse.y)
                                }
                            }
                            onPositionChanged: function(mouse) {
                                lastX = mouse.x; lastY = mouse.y
                                EditorController.mouseMove(mouse.x, mouse.y)
                            }
                            onReleased: function(mouse) {
                                EditorController.mouseRelease(mouse.x, mouse.y)
                            }
                        }
                }

                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            }
        }

        // — 右侧属性面板 —
        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: bgSidebar
            border.color: borderColor

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                // 当前工具名
                Text {
                    text: "工具: " + currentTool
                    color: accentColor
                    font.pixelSize: 13
                    font.family: "Microsoft YaHei"
                    font.bold: true
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderColor }

                // 颜色选择区域
                Text {
                    text: "颜色"
                    color: txtSecondary
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                }

                // 预设颜色网格
                GridLayout {
                    columns: 4
                    rowSpacing: 4
                    columnSpacing: 4

                    property var colors: [
                        "#FF3B30", "#FF9500", "#FFCC02", "#34C759",
                        "#007AFF", "#5856D6", "#AF52DE", "#FF2D55",
                        "#FF6B35", "#30D158", "#5AC8FA", "#FFD60A",
                        "#8E8E93", "#FF375F", "#64D2FF", "#32D74B"
                    ]

                    Repeater {
                        model: 16
                        Rectangle {
                            width: 36; height: 36; radius: 6
                            color: parent.colors[index]
                            border.width: toolColor === parent.colors[index] ? 3 : 1
                            border.color: toolColor === parent.colors[index] ?
                                          "#ffffff" : (colorPickerHover.hovered ? borderColor : "transparent")

                            MouseArea {
                                id: colorPickerHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    toolColor = parent.parent.colors[index]
                                    EditorController.setColor(toolColor)
                                }
                            }
                        }
                    }
                }

                // 自定义颜色输入
                RowLayout {
                    Rectangle {
                        width: 28; height: 28; radius: 4
                        color: toolColor
                        border.color: borderColor
                    }
                    TextInput {
                        id: colorInput
                        text: toolColor
                        color: txtPrimary
                        font.pixelSize: 12
                        font.family: "Consolas, monospace"
                        Layout.fillWidth: true
                        maximumLength: 7
                        validator: RegularExpressionValidator { regularExpression: /#[0-9A-Fa-f]{0,6}/ }
                        onEditingFinished: {
                            if (text.length === 7 && /^#[0-9A-Fa-f]{6}$/.test(text)) {
                                toolColor = text
                                EditorController.setColor(text)
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderColor }

                // 笔触宽度
                Text {
                    text: "笔触: " + toolWidth + "px"
                    color: txtSecondary
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                }

                Slider {
                    id: widthSlider
                    Layout.fillWidth: true
                    from: toolMinWidth
                    to: toolMaxWidth
                    stepSize: 1
                    live: true
                    implicitHeight: 36

                    // 拖拽状态标记 — 避免绑定循环
                    property bool userDragging: false

                    // 仅在非拖拽时同步 toolWidth → slider 位置
                    Binding on value {
                        when: !widthSlider.userDragging
                        value: toolWidth
                    }

                    background: Rectangle {
                        x: widthSlider.leftPadding
                        y: widthSlider.topPadding + widthSlider.availableHeight/2 - 2
                        width: widthSlider.availableWidth
                        height: 4
                        radius: 2
                        color: borderColor
                        Rectangle {
                            width: widthSlider.visualPosition * parent.width
                            height: parent.height
                            color: accentColor
                            radius: 2
                        }
                    }
                    handle: Rectangle {
                        x: widthSlider.leftPadding + widthSlider.visualPosition * (widthSlider.availableWidth - width)
                        y: widthSlider.topPadding + widthSlider.availableHeight/2 - height/2
                        width: 16; height: 16; radius: 8
                        color: accentColor
                        border.color: "#ffffff"; border.width: 2
                    }

                    onPressedChanged: { userDragging = pressed }
                    onMoved: {
                        toolWidth = Math.round(value)
                        EditorController.setWidth(toolWidth)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderColor }

                // 不透明度
                Text {
                    text: "不透明度: " + toolOpacity
                    color: txtSecondary
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                }

                Slider {
                    id: opacitySlider
                    Layout.fillWidth: true
                    from: 20; to: 255
                    stepSize: 5
                    live: true
                    implicitHeight: 36

                    property bool userDragging: false
                    Binding on value {
                        when: !opacitySlider.userDragging
                        value: toolOpacity
                    }

                    background: Rectangle {
                        x: opacitySlider.leftPadding
                        y: opacitySlider.topPadding + opacitySlider.availableHeight/2 - 2
                        width: opacitySlider.availableWidth
                        height: 4; radius: 2; color: borderColor
                        Rectangle {
                            width: opacitySlider.visualPosition * parent.width
                            height: parent.height; color: accentColor; radius: 2
                        }
                    }
                    handle: Rectangle {
                        x: opacitySlider.leftPadding + opacitySlider.visualPosition * (opacitySlider.availableWidth - width)
                        y: opacitySlider.topPadding + opacitySlider.availableHeight/2 - height/2
                        width: 16; height: 16; radius: 8
                        color: accentColor
                        border.color: "#ffffff"; border.width: 2
                    }

                    onPressedChanged: { userDragging = pressed }
                    onMoved: {
                        toolOpacity = Math.round(value)
                        EditorController.setOpacity(toolOpacity)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderColor }

                // 水印工具参数面板
                ColumnLayout {
                    visible: currentTool === "watermark"
                    spacing: 10
                    Layout.fillWidth: true

                    Text {
                        text: "水印设置"
                        color: accentColor
                        font.pixelSize: 12
                        font.bold: true
                        font.family: "Microsoft YaHei"
                    }

                    // 水印文字
                    Text {
                        text: "文字:"
                        color: txtSecondary
                        font.pixelSize: 11
                        font.family: "Microsoft YaHei"
                    }
                    TextField {
                        id: watermarkText
                        Layout.fillWidth: true
                        text: "水印"
                        font.pixelSize: 12
                        font.family: "Microsoft YaHei"
                        color: txtPrimary
                        background: Rectangle {
                            color: isDark ? "#181828" : "#f8f9fb"
                            radius: 4
                            border.color: borderColor
                        }
                        onEditingFinished: {
                            EditorController.updateWatermarkPreview(
                                watermarkText.text,
                                Math.round(watermarkOpacity.value),
                                Math.round(watermarkSize.value),
                                Math.round(watermarkRotation.value),
                                watermarkCenterBtn.active ? "center" : "tile"
                            )
                        }
                    }

                    // 透明度
                    Text {
                        text: "透明度: " + watermarkOpacity.value
                        color: txtSecondary
                        font.pixelSize: 11
                        font.family: "Microsoft YaHei"
                    }
                    Slider {
                        id: watermarkOpacity
                        Layout.fillWidth: true
                        from: 5; to: 100; stepSize: 5
                        live: true
                        implicitHeight: 30
                        value: 25  // 水印滑块初始值固定，无需动态绑定
                        background: Rectangle {
                            x: watermarkOpacity.leftPadding
                            y: watermarkOpacity.topPadding + watermarkOpacity.availableHeight/2 - 2
                            width: watermarkOpacity.availableWidth; height: 4
                            radius: 2; color: borderColor
                            Rectangle {
                                width: watermarkOpacity.visualPosition * parent.width
                                height: parent.height; color: accentColor; radius: 2
                            }
                        }
                        handle: Rectangle {
                            x: watermarkOpacity.leftPadding + watermarkOpacity.visualPosition * (watermarkOpacity.availableWidth - 12)
                            y: watermarkOpacity.topPadding + watermarkOpacity.availableHeight/2 - 6
                            width: 12; height: 12; radius: 6
                            color: accentColor
                            border.color: "#ffffff"; border.width: 1.5
                        }
                        onMoved: {
                            EditorController.updateWatermarkPreview(
                                watermarkText.text,
                                Math.round(watermarkOpacity.value),
                                Math.round(watermarkSize.value),
                                Math.round(watermarkRotation.value),
                                watermarkCenterBtn.active ? "center" : "tile"
                            )
                        }
                    }

                    // 大小
                    Text {
                        text: "大小: " + watermarkSize.value
                        color: txtSecondary
                        font.pixelSize: 11
                        font.family: "Microsoft YaHei"
                    }
                    Slider {
                        id: watermarkSize
                        Layout.fillWidth: true
                        from: 12; to: 200; stepSize: 2
                        live: true
                        implicitHeight: 30
                        value: 52
                        background: Rectangle {
                            x: watermarkSize.leftPadding
                            y: watermarkSize.topPadding + watermarkSize.availableHeight/2 - 2
                            width: watermarkSize.availableWidth; height: 4
                            radius: 2; color: borderColor
                            Rectangle {
                                width: watermarkSize.visualPosition * parent.width
                                height: parent.height; color: accentColor; radius: 2
                            }
                        }
                        handle: Rectangle {
                            x: watermarkSize.leftPadding + watermarkSize.visualPosition * (watermarkSize.availableWidth - 12)
                            y: watermarkSize.topPadding + watermarkSize.availableHeight/2 - 6
                            width: 12; height: 12; radius: 6
                            color: accentColor
                            border.color: "#ffffff"; border.width: 1.5
                        }
                        onMoved: {
                            EditorController.updateWatermarkPreview(
                                watermarkText.text,
                                Math.round(watermarkOpacity.value),
                                Math.round(watermarkSize.value),
                                Math.round(watermarkRotation.value),
                                watermarkCenterBtn.active ? "center" : "tile"
                            )
                        }
                    }

                    // 旋转角度
                    Text {
                        text: "旋转: " + watermarkRotation.value + "°"
                        color: txtSecondary
                        font.pixelSize: 11
                        font.family: "Microsoft YaHei"
                    }
                    Slider {
                        id: watermarkRotation
                        Layout.fillWidth: true
                        from: 0; to: 90; stepSize: 1
                        live: true
                        implicitHeight: 30
                        value: 28
                        background: Rectangle {
                            x: watermarkRotation.leftPadding
                            y: watermarkRotation.topPadding + watermarkRotation.availableHeight/2 - 2
                            width: watermarkRotation.availableWidth; height: 4
                            radius: 2; color: borderColor
                            Rectangle {
                                width: watermarkRotation.visualPosition * parent.width
                                height: parent.height; color: accentColor; radius: 2
                            }
                        }
                        handle: Rectangle {
                            x: watermarkRotation.leftPadding + watermarkRotation.visualPosition * (watermarkRotation.availableWidth - 12)
                            y: watermarkRotation.topPadding + watermarkRotation.availableHeight/2 - 6
                            width: 12; height: 12; radius: 6
                            color: accentColor
                            border.color: "#ffffff"; border.width: 1.5
                        }
                        onMoved: {
                            EditorController.updateWatermarkPreview(
                                watermarkText.text,
                                Math.round(watermarkOpacity.value),
                                Math.round(watermarkSize.value),
                                Math.round(watermarkRotation.value),
                                watermarkCenterBtn.active ? "center" : "tile"
                            )
                        }
                    }

                    // 模式选择
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "模式:"
                            color: txtSecondary
                            font.pixelSize: 11
                            font.family: "Microsoft YaHei"
                        }
                        Button {
                            id: watermarkModeBtn
                            text: "平铺"
                            font.pixelSize: 11
                            font.family: "Microsoft YaHei"
                            flat: true
                            property bool active: true
                            background: Rectangle {
                                color: parent.active ? accentColor :
                                       (parent.hovered ? hoverColor : "transparent")
                                radius: 4
                                border.color: parent.active ? accentColor : borderColor
                            }
                            contentItem: Text {
                                text: parent.text
                                color: parent.active ? "#ffffff" : txtPrimary
                                font: parent.font
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: {
                                watermarkModeBtn.active = true;
                                watermarkCenterBtn.active = false;
                                EditorController.updateWatermarkPreview(
                                    watermarkText.text,
                                    Math.round(watermarkOpacity.value),
                                    Math.round(watermarkSize.value),
                                    Math.round(watermarkRotation.value),
                                    "tile"
                                )
                            }
                        }
                        Button {
                            id: watermarkCenterBtn
                            text: "居中"
                            font.pixelSize: 11
                            font.family: "Microsoft YaHei"
                            flat: true
                            property bool active: false
                            background: Rectangle {
                                color: parent.active ? accentColor :
                                       (parent.hovered ? hoverColor : "transparent")
                                radius: 4
                                border.color: parent.active ? accentColor : borderColor
                            }
                            contentItem: Text {
                                text: parent.text
                                color: parent.active ? "#ffffff" : txtPrimary
                                font: parent.font
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: {
                                watermarkModeBtn.active = false;
                                watermarkCenterBtn.active = true;
                                EditorController.updateWatermarkPreview(
                                    watermarkText.text,
                                    Math.round(watermarkOpacity.value),
                                    Math.round(watermarkSize.value),
                                    Math.round(watermarkRotation.value),
                                    "center"
                                )
                            }
                        }
                    }

                    // 应用按钮
                    Button {
                        Layout.fillWidth: true
                        text: "应用到截图"
                        font.pixelSize: 12
                        font.family: "Microsoft YaHei"
                        background: Rectangle {
                            color: parent.hovered ? accentColor : "transparent"
                            radius: 4
                            border.color: accentColor
                            border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.hovered ? "#ffffff" : accentColor
                            font: parent.font
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            var mode = watermarkCenterBtn.active ? "center" : "tile"
                            EditorController.setWatermarkParams(
                                watermarkText.text,
                                Math.round(watermarkOpacity.value),
                                Math.round(watermarkSize.value),
                                Math.round(watermarkRotation.value),
                                mode
                            )
                            showToast("水印已应用", "success")
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: borderColor }
                }

                Item { Layout.fillHeight: true }

                // 快捷操作
                Button {
                    Layout.fillWidth: true
                    text: "清除所有标注"
                    flat: true
                    contentItem: Text {
                        text: parent.text
                        color: dangerColor
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.hovered ? hoverColor : "transparent"
                        radius: 4; border.color: borderColor; border.width: 1
                    }
                    onClicked: EditorController.clearAll()
                }
            }
        }
    }

    // ============ 底部状态栏 ============
    footer: Rectangle {
        color: bgToolbar
        height: 28
        border.color: borderColor

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10

            Text {
                text: imageWidth + " × " + imageHeight + " px"
                color: txtSecondary
                font.pixelSize: 11
                font.family: "Microsoft YaHei"
            }

            Rectangle { width: 1; height: 14; color: borderColor }

            Text {
                text: "工具: " + currentTool
                color: accentColor
                font.pixelSize: 11
                font.family: "Microsoft YaHei"
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "滚轮缩放 | Ctrl+Z 撤销 | Ctrl+S 保存"
                color: txtSecondary
                font.pixelSize: 11
                font.family: "Microsoft YaHei"
            }
        }
    }

    // ============ Connections ============

    // 监听Canvas需要重绘
    Connections {
        target: EditorController
        function onCanvasNeedsUpdate() {
            var jsonStr = EditorController.getAnnotationsJson()
            try {
                annotationCanvas.annotationsData = JSON.parse(jsonStr)
            } catch (e) {
                annotationCanvas.annotationsData = []
            }
            annotationCanvas.requestPaint()
        }
        function onPreviewUpdated(jsonStr) {
            if (jsonStr) {
                try {
                    annotationCanvas.previewData = JSON.parse(jsonStr)
                } catch (e) {
                    annotationCanvas.previewData = null
                }
            } else {
                annotationCanvas.previewData = null
            }
            annotationCanvas.requestPaint()
        }
        function onUndoStateChanged(u, r) {
            canUndo = u
            canRedo = r
        }
        function onImageSourceChanged(newPath) {
            // 破坏性工具（马赛克/橡皮擦/水印）应用后，更新底图
            imagePath = newPath
            imagePreview.reloadToken = Date.now()
            imagePreview.source = "file:///" + newPath + "?t=" + imagePreview.reloadToken
            annotationCanvas.requestPaint()
        }
        function onExportFinished(filePath) {
            if (filePath && filePath !== "") {
                var name = filePath.split('/').pop() || filePath.split('\\').pop()
                showToast("已保存: " + name, "success")
            }
        }
    }

    // 保存按钮增强 — 显示结果
    function doSave() {
        var result = EditorController.saveToFile()
        if (result === "cancel") return
        if (result.startsWith("error")) {
            showToast("保存失败: " + result.replace("error:", ""), "error")
        } else if (result) {
            var name = result.split('/').pop() || result.split('\\').pop()
            showToast("已保存: " + name, "success")
        }
    }

    function doCopy() {
        var result = EditorController.copyToClipboard()
        if (result === "ok") {
            showToast("已复制到剪贴板", "success")
        } else {
            showToast("复制失败", "error")
        }
    }

    // Toast 浮动提示
    Rectangle {
        id: toastBox
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 40
        z: 100
        width: toastText.implicitWidth + 36
        height: 36
        radius: 8
        visible: toastOn
        opacity: toastOn ? 0.95 : 0
        color: toastKind === "success" ? "#1a3a1a" :
               (toastKind === "error" ? "#3a1a1a" : "#1e1e3a")
        border.color: toastKind === "success" ? successColor :
                      (toastKind === "error" ? dangerColor : accentColor)
        border.width: 1

        Behavior on opacity { NumberAnimation { duration: 200 } }

        Text {
            id: toastText
            anchors.centerIn: parent
            text: toastMsg
            color: toastKind === "success" ? successColor :
                   (toastKind === "error" ? dangerColor : txtPrimary)
            font.pixelSize: 12
            font.family: "Microsoft YaHei"
        }
    }

    // ============ 文字输入对话框（模态 Dialog，参考高星项目做法） ============
    Dialog {
        id: textInputDialog
        title: "输入文字"
        modal: true
        focus: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        x: (editorWindow.width - width) / 2
        y: (editorWindow.height - height) / 2
        width: 340

        property int mouseX: 0
        property int mouseY: 0

        contentItem: ColumnLayout {
            spacing: 12

            Text {
                text: "文字内容"
                color: accentColor
                font.pixelSize: 13; font.bold: true
                font.family: "Microsoft YaHei"
            }

            // 多行文本框（Ctrl+Enter 确认，Esc 取消）
            TextArea {
                id: textInputField
                Layout.fillWidth: true
                implicitHeight: 72
                text: "文字"
                font.pixelSize: 14
                font.family: "Microsoft YaHei"
                color: txtPrimary
                wrapMode: TextArea.Wrap
                selectByMouse: true
                background: Rectangle {
                    color: isDark ? "#181828" : "#f8f9fb"
                    radius: 4
                    border.color: borderColor
                }
                Keys.onEscapePressed: textInputDialog.reject()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Return &&
                        (event.modifiers & Qt.ControlModifier)) {
                        textInputDialog.accept()
                        event.accepted = true
                    }
                }
            }

            // 字体大小
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "字号: " + fontSizeSlider.value
                    color: txtSecondary
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                }
                Slider {
                    id: fontSizeSlider
                    Layout.fillWidth: true
                    from: 12; to: 72; stepSize: 1
                    live: true
                    implicitHeight: 30
                    value: 20
                    background: Rectangle {
                        x: fontSizeSlider.leftPadding
                        y: fontSizeSlider.topPadding + fontSizeSlider.availableHeight/2 - 2
                        width: fontSizeSlider.availableWidth; height: 4
                        radius: 2; color: borderColor
                        Rectangle {
                            width: fontSizeSlider.visualPosition * parent.width
                            height: parent.height; color: accentColor; radius: 2
                        }
                    }
                    handle: Rectangle {
                        x: fontSizeSlider.leftPadding + fontSizeSlider.visualPosition * (fontSizeSlider.availableWidth - 12)
                        y: fontSizeSlider.topPadding + fontSizeSlider.availableHeight/2 - 6
                        width: 12; height: 12; radius: 6
                        color: accentColor
                        border.color: "#ffffff"; border.width: 1.5
                    }
                }
            }

            // 加粗 / 背景 选项
            RowLayout {
                Layout.fillWidth: true
                spacing: 16
                CheckBox {
                    id: textBoldChk
                    text: "加粗"
                    checked: false
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 12
                }
                CheckBox {
                    id: textBgChk
                    text: "背景"
                    checked: false
                    font.family: "Microsoft YaHei"
                    font.pixelSize: 12
                }
            }
        }

        onAboutToShow: {
            // 重置为初始状态，避免上一次残留
            textInputField.text = "文字"
            fontSizeSlider.value = 20
            textBoldChk.checked = false
            textBgChk.checked = false
            // 本地化标准按钮文字
            if (standardButton(Dialog.Ok)) standardButton(Dialog.Ok).text = "确定"
            if (standardButton(Dialog.Cancel)) standardButton(Dialog.Cancel).text = "取消"
            textInputField.forceActiveFocus()
            textInputField.selectAll()
        }

        onAccepted: {
            var text = textInputField.text
            if (text.length > 0) {
                // 先记录锚点位置，再设置文字（多行 / 加粗 / 背景）
                EditorController.mousePress(mouseX, mouseY)
                EditorController.setTextAnnotation(
                    text, fontSizeSlider.value,
                    textBoldChk.checked, textBgChk.checked)
                showToast("文字已添加", "success")
            }
        }
    }

    // 初始化: 加载标注数据
    Component.onCompleted: {
        var jsonStr = EditorController.getAnnotationsJson()
        try {
            annotationCanvas.annotationsData = JSON.parse(jsonStr)
        } catch (e) {
            annotationCanvas.annotationsData = []
        }
        annotationCanvas.requestPaint()

        // 默认选择画笔工具
        EditorController.selectTool("brush")
        var cfg = JSON.parse(EditorController.getToolMinWidth())
        toolMinWidth = cfg.min
        toolMaxWidth = cfg.max
        toolWidth = Math.round((cfg.min + cfg.max) / 3)
        EditorController.setWidth(toolWidth)
    }

    // 关闭时通知Python清理
    onClosing: {
        EditorController.closeEditor()
    }
}
