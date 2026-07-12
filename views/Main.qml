// 主窗口 QML — 欢迎页 + 历史记录 + 设置
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 960
    height: 680
    minimumWidth: 640
    minimumHeight: 440
    title: "截图软件 v5.0"
    flags: Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint

    // 主题颜色绑定
    property var themeColors: ThemeManager ? ThemeManager.getTheme() : ({})
    property color bgApp: themeColors.background ? themeColors.background.app : "#141422"
    property color bgCard: themeColors.background ? themeColors.background.card : "#1e1e32"
    property color txtPrimary: themeColors.text ? themeColors.text.primary : "#f0f0f8"
    property color txtSecondary: themeColors.text ? themeColors.text.secondary : "#b0b0c8"
    property color accentColor: themeColors.accent ? themeColors.accent.primary : "#4a8cff"
    property color borderColor: themeColors.border ? themeColors.border.default : "#2a2a44"
    property color dangerColor: themeColors.semantic ? themeColors.semantic.error : "#e05555"
    property bool isDark: ThemeManager ? ThemeManager.isDark() : true
    property color hoverColor: isDark ? "#333358" : "#eef1f6"
    property int currentTab: 0   // 0=欢迎, 1=历史
    property string toastMessage: ""
    property bool toastVisible: false
    property string toastType: "info"  // "success", "error", "info"

    color: bgApp

    // 连接截图控制器信号
    Connections {
        target: ScreenshotController
        function onCaptureStarted(mode) {
            if (mode === "region") { mainWindow.hide() }
        }
        function onCaptureCancelled() {
            mainWindow.show()
            mainWindow.raise()
        }
        function onScreenshotReady(path, w, h) {
            // 不在这里show主窗口，编辑器打开期间主窗口保持隐藏
            // 编辑器关闭后由 main.py 的 _onEditorClosed 恢复主窗口
            _showToast("截图成功 " + w + "×" + h + "px", "success")
        }
    }

    // Toast 提示
    function _showToast(msg, type) {
        toastMessage = msg
        toastType = type || "info"
        toastVisible = true
        toastTimer.restart()
    }

    Timer {
        id: toastTimer
        interval: 2500
        onTriggered: toastVisible = false
    }

    // 顶部工具栏
    header: Rectangle {
        id: headerBar
        color: bgCard
        height: 52
        border.color: borderColor
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 6

            // Logo
            Text {
                text: "截图软件"
                font.pixelSize: 18
                font.bold: true
                font.family: "Microsoft YaHei, 微软雅黑"
                color: accentColor
                Layout.alignment: Qt.AlignVCenter
            }

            Rectangle { width: 1; height: 24; color: borderColor; Layout.alignment: Qt.AlignVCenter; Layout.leftMargin: 6 }

            // 截图模式按钮
            ToolButton {
                text: "全屏截图"
                ToolTip { text: "截取整个屏幕 (Ctrl+Shift+F)"; visible: parent.hovered; delay: 400 }
                contentItem: Text {
                    text: parent.text; color: txtPrimary; font.pixelSize: 12
                    font.family: "Microsoft YaHei"
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: ScreenshotController.captureFullscreen()
            }
            ToolButton {
                text: "区域截图"
                ToolTip { text: "拖拽选择截图区域 (Ctrl+Shift+R)"; visible: parent.hovered; delay: 400 }
                contentItem: Text {
                    text: parent.text; color: txtPrimary; font.pixelSize: 12
                    font.family: "Microsoft YaHei"
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: ScreenshotController.captureRegion()
            }
            ToolButton {
                text: "窗口截图"
                ToolTip { text: "截取当前鼠标下的窗口 (Ctrl+Shift+W)"; visible: parent.hovered; delay: 400 }
                contentItem: Text {
                    text: parent.text; color: txtPrimary; font.pixelSize: 12
                    font.family: "Microsoft YaHei"
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: ScreenshotController.captureWindow()
            }
            ToolButton {
                text: "滚动截图"
                ToolTip { text: "长页面滚动截取"; visible: parent.hovered; delay: 400 }
                contentItem: Text {
                    text: parent.text; color: txtPrimary; font.pixelSize: 12
                    font.family: "Microsoft YaHei"
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: ScreenshotController.captureScrolling()
            }

            Item { Layout.fillWidth: true }

            // 标签页切换
            TabBar {
                id: tabBar
                Layout.alignment: Qt.AlignVCenter
                background: Rectangle { color: "transparent" }

                TabButton {
                    text: "首页"
                    font.family: "Microsoft YaHei"; font.pixelSize: 11
                    contentItem: Text { text: parent.text; color: currentTab === 0 ? accentColor : txtSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle {
                        color: currentTab === 0 ? Qt.rgba(0.29, 0.55, 1, 0.1) :
                               (parent.hovered ? hoverColor : "transparent")
                        radius: 4
                    }
                    onClicked: currentTab = 0
                }
                TabButton {
                    text: "历史"
                    font.family: "Microsoft YaHei"; font.pixelSize: 11
                    contentItem: Text { text: parent.text; color: currentTab === 1 ? accentColor : txtSecondary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle {
                        color: currentTab === 1 ? Qt.rgba(0.29, 0.55, 1, 0.1) :
                               (parent.hovered ? hoverColor : "transparent")
                        radius: 4
                    }
                    onClicked: { currentTab = 1; historyPanel.refresh() }
                }
            }

            ToolButton {
                text: "⚙ 设置"
                ToolTip { text: "应用设置"; visible: parent.hovered; delay: 400 }
                contentItem: Text { text: parent.text; color: txtSecondary; font.pixelSize: 12; font.family: "Microsoft YaHei"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: settingsDialog.open()
            }
            ToolButton {
                text: "✕"
                ToolTip { text: "关闭"; visible: parent.hovered; delay: 400 }
                contentItem: Text { text: parent.text; color: dangerColor; font.pixelSize: 14; font.family: "Microsoft YaHei"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: parent.hovered ? hoverColor : "transparent"; radius: 4 }
                onClicked: Qt.quit()
            }
        }
    }

    // 主内容区 — StackLayout 切换欢迎页/历史页
    StackLayout {
        anchors.fill: parent
        currentIndex: currentTab

        // Page 0: 欢迎页
        Rectangle {
            color: bgApp

            Column {
                anchors.centerIn: parent
                spacing: 24

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 80; height: 80; radius: 20
                    color: accentColor; opacity: 0.15
                    Text { anchors.centerIn: parent; text: "📷"; font.pixelSize: 36 }
                }

                Column {
                    spacing: 8
                    anchors.horizontalCenter: parent.horizontalCenter

                    Text {
                        text: "截图软件"
                        font.pixelSize: 28; font.bold: true
                        font.family: "Microsoft YaHei, 微软雅黑"; color: txtPrimary
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: "离线截图 + 标注工具"
                        font.pixelSize: 14; font.family: "Microsoft YaHei, 微软雅黑"; color: txtSecondary
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }

                // 快捷键提示
                Row {
                    spacing: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                    Repeater {
                        model: [
                            { key: "Ctrl+Shift+F", desc: "全屏截图" },
                            { key: "Ctrl+Shift+R", desc: "区域截图" },
                            { key: "Ctrl+Shift+W", desc: "窗口截图" },
                            { key: "Esc", desc: "取消操作" }
                        ]
                        Rectangle {
                            width: 130; height: 56; radius: 8
                            color: bgCard; border.color: borderColor
                            Column {
                                anchors.centerIn: parent; spacing: 4
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.key; font.pixelSize: 13; font.bold: true; font.family: "Consolas, Microsoft YaHei"; color: accentColor }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.desc; font.pixelSize: 11; font.family: "Microsoft YaHei"; color: txtSecondary }
                            }
                        }
                    }
                }

                // 快捷按钮
                Row {
                    spacing: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                    Button {
                        text: "开始截图"; font.family: "Microsoft YaHei"; font.pixelSize: 14
                        onClicked: ScreenshotController.captureRegion()
                        background: Rectangle { color: accentColor; radius: 8 }
                        contentItem: Text { text: parent.text; color: "#FFFFFF"; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                    Button {
                        text: "快速全屏"; font.family: "Microsoft YaHei"; font.pixelSize: 14
                        onClicked: ScreenshotController.captureFullscreen()
                        background: Rectangle { color: "transparent"; radius: 8; border.color: borderColor }
                        contentItem: Text { text: parent.text; color: txtPrimary; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
        }

        // Page 1: 历史记录
        HistoryView {
            id: historyPanel
        }
    }

    // Toast 浮动提示
    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 40
        width: toastLabel.implicitWidth + 40
        height: 40
        radius: 8
        visible: toastVisible
        opacity: toastVisible ? 0.95 : 0
        color: toastType === "success" ? "#1a3a1a" :
               (toastType === "error" ? "#3a1a1a" : "#1e1e3a")
        border.color: toastType === "success" ? "#51cf66" :
                      (toastType === "error" ? "#ff6b6b" : "#4a8cff")
        border.width: 1

        Behavior on opacity { NumberAnimation { duration: 200 } }

        Text {
            id: toastLabel
            anchors.centerIn: parent
            text: toastMessage
            color: toastType === "success" ? "#51cf66" :
                   (toastType === "error" ? "#ff6b6b" : "#f0f0f8")
            font.pixelSize: 13
            font.family: "Microsoft YaHei"
        }
    }

    // 设置对话框
    Dialog {
        id: settingsDialog
        title: "设置"
        modal: true
        anchors.centerIn: parent
        width: 480
        padding: 20

        background: Rectangle { color: bgCard; radius: 12; border.color: borderColor }

        property string savePath: ConfigManager ? ConfigManager.get("app_config", "save_path", "") : ""
        property int formatIndex: {
            var fmt = ConfigManager ? ConfigManager.get("app_config", "file_format", "PNG") : "PNG"
            return ["PNG","JPG","BMP","PDF"].indexOf(fmt)
        }
        property bool autoCopy: ConfigManager ? ConfigManager.get("app_config", "auto_copy", true) : true
        property int themeIndex: ThemeManager ? (ThemeManager.isDark() ? 0 : 1) : 0

        header: Rectangle {
            color: "transparent"
            height: 36
            Text {
                anchors.centerIn: parent
                text: settingsDialog.title
                font.pixelSize: 16; font.bold: true
                font.family: "Microsoft YaHei"; color: txtPrimary
            }
        }

        ColumnLayout {
            spacing: 16
            width: parent.width

            // 外观
            GroupBox {
                title: "外观"
                Layout.fillWidth: true

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    Text { text: "主题:"; color: txtPrimary; font.family: "Microsoft YaHei"; Layout.preferredWidth: 60 }
                    ComboBox {
                        id: themeCombo
                        model: ["深色", "浅色"]
                        currentIndex: settingsDialog.themeIndex
                        Layout.fillWidth: true
                        onCurrentIndexChanged: {
                            ThemeManager.switchTheme(currentIndex === 0 ? "dark" : "light")
                        }
                    }
                }
            }

            // 保存
            GroupBox {
                title: "保存"
                Layout.fillWidth: true

                ColumnLayout {
                    spacing: 10
                    Layout.fillWidth: true

                    RowLayout {
                        Text { text: "路径:"; color: txtPrimary; font.family: "Microsoft YaHei"; Layout.preferredWidth: 60 }
                        TextField {
                            id: pathField
                            Layout.fillWidth: true
                            text: settingsDialog.savePath
                            font.family: "Microsoft YaHei"
                            color: txtPrimary
                            background: Rectangle { color: "#2a2a4c"; radius: 4; border.color: borderColor }

                            // 长路径省略显示
                            property string shortPath: {
                                var p = text
                                if (p.length <= 35) return p
                                var parts = p.split(/[\\/]/)
                                if (parts.length <= 2) return p
                                return parts[0] + "/.../" + parts[parts.length-1]
                            }
                            // displayText 是只读属性，改为直接显示完整路径
                        }
                        Button {
                            text: "浏览"
                            font.family: "Microsoft YaHei"
                            onClicked: {
                                var folder = ScreenshotController.browseFolder()
                                if (folder) {
                                    pathField.text = folder
                                }
                            }
                        }
                    }

                    RowLayout {
                        Text { text: "格式:"; color: txtPrimary; font.family: "Microsoft YaHei"; Layout.preferredWidth: 60 }
                        ComboBox {
                            id: formatCombo
                            model: ["PNG", "JPG", "BMP", "PDF"]
                            currentIndex: settingsDialog.formatIndex
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // 操作
            GroupBox {
                title: "操作"
                Layout.fillWidth: true

                CheckBox {
                    id: autoCopyCheck
                    text: "截图后自动复制到剪贴板"
                    font.family: "Microsoft YaHei"
                    checked: settingsDialog.autoCopy
                    contentItem: Text {
                        text: parent.text; color: txtPrimary; font: parent.font
                        leftPadding: parent.indicator.width + parent.spacing
                    }
                }
            }

            // 按钮
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8

                Button {
                    text: "取消"
                    font.family: "Microsoft YaHei"
                    flat: true
                    onClicked: settingsDialog.close()
                }

                Button {
                    text: "保存设置"
                    font.family: "Microsoft YaHei"
                    background: Rectangle { color: accentColor; radius: 6 }
                    contentItem: Text { text: parent.text; color: "#FFFFFF"; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }

                    onClicked: {
                        // 保存所有设置到ConfigManager
                        if (ConfigManager) {
                            ConfigManager.set("app_config", "save_path", pathField.text)
                            ConfigManager.set("app_config", "file_format", formatCombo.currentText)
                            ConfigManager.set("app_config", "auto_copy", autoCopyCheck.checked)
                            ConfigManager.set("app_config", "theme",
                                themeCombo.currentIndex === 0 ? "dark" : "light")
                        }
                        _showToast("设置已保存", "success")
                        settingsDialog.close()
                    }
                }
            }
        }
    }

    // 键盘快捷键 — 截图类快捷由keyboard库全局钩子处理（main.py _onGlobalHotkey）
    // 避免与全局钩子双重触发导致状态异常
    // 主窗口按钮保留可用：快捷键失效时用户仍可点击按钮

    onClosing: Qt.quit()

    Component.onCompleted: {
        x = Screen.width / 2 - width / 2
        y = Screen.height / 2 - height / 2
    }
}
