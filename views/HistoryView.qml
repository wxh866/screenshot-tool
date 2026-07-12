// 历史记录浏览面板
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: historyRoot
    color: bgApp

    // 主题颜色绑定
    property var themeColors: ThemeManager ? ThemeManager.getTheme() : ({})
    property color bgApp: themeColors.background ? themeColors.background.app : "#141422"
    property color bgCard: themeColors.background ? themeColors.background.card : "#1e1e32"
    property color txtPrimary: themeColors.text ? themeColors.text.primary : "#f0f0f8"
    property color txtSecondary: themeColors.text ? themeColors.text.secondary : "#b0b0c8"
    property color accentColor: themeColors.accent ? themeColors.accent.primary : "#4a8cff"
    property color borderColor: themeColors.border ? themeColors.border.default : "#2a2a44"
    property bool isDark: ThemeManager ? ThemeManager.isDark() : true
    property color hoverColor: isDark ? "#333358" : "#eef1f6"

    property var historyItems: []
    property string statusText: ""

    // 加载历史记录
    function refresh() {
        var jsonStr = HistoryController.getRecentHistory()
        try {
            historyItems = JSON.parse(jsonStr)
            statusText = historyItems.length + " 条截屏记录"
        } catch (e) {
            historyItems = []
            statusText = "无历史记录"
        }
    }

    // 顶部标题栏
    Rectangle {
        id: titleBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 40
        color: bgCard

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16

            Text {
                text: "截屏历史"
                font.pixelSize: 14
                font.bold: true
                font.family: "Microsoft YaHei"
                color: accentColor
            }

            Item { Layout.fillWidth: true }

            Text {
                text: statusText
                font.pixelSize: 11
                font.family: "Microsoft YaHei"
                color: txtSecondary
            }

            Button {
                text: "刷新"
                font.pixelSize: 11
                font.family: "Microsoft YaHei"
                flat: true
                contentItem: Text {
                    text: parent.text
                    color: txtSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.hovered ? hoverColor : "transparent"
                    radius: 4
                }
                onClicked: refresh()
            }
        }
    }

    // 空状态
    Column {
        anchors.centerIn: parent
        visible: historyItems.length === 0
        spacing: 12

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "还没有截屏记录"
            font.pixelSize: 16
            font.family: "Microsoft YaHei"
            color: txtSecondary
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "使用上方按钮开始截图"
            font.pixelSize: 12
            font.family: "Microsoft YaHei"
            color: txtSecondary
            opacity: 0.6
        }
    }

    // 缩略图网格
    ScrollView {
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        GridView {
            id: historyGrid
            anchors.fill: parent
            anchors.margins: 20
            cellWidth: 220
            cellHeight: 180
            model: historyItems
            clip: true

            delegate: Rectangle {
                width: historyGrid.cellWidth - 12
                height: historyGrid.cellHeight - 12
                radius: 8
                color: bgCard
                border.color: borderColor
                border.width: 1

                // 缩略图
                Image {
                    id: thumbImg
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 8
                    height: parent.height - 55
                    source: modelData.thumbnail_path ?
                        "file:///" + modelData.thumbnail_path : ""
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    cache: false

                    // 占位符
                    Rectangle {
                        anchors.fill: parent
                        color: borderColor
                        visible: thumbImg.source === "" ||
                                 thumbImg.status === Image.Error
                        Text {
                            anchors.centerIn: parent
                            text: "无预览"
                            color: txtSecondary
                            opacity: 0.5
                            font.pixelSize: 11
                        }
                    }
                }

                // 信息栏
                RowLayout {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 8
                    height: 40

                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true

                        Text {
                            text: {
                                var d = new Date(modelData.timestamp * 1000)
                                return d.toLocaleDateString() + " " +
                                       d.toLocaleTimeString(Qt.locale(), "hh:mm")
                            }
                            font.pixelSize: 10
                            font.family: "Microsoft YaHei"
                            color: txtSecondary
                            elide: Text.ElideRight
                        }
                        Text {
                            text: modelData.annotations_count + " 标注"
                            font.pixelSize: 9
                            font.family: "Microsoft YaHei"
                            color: accentColor
                        }
                    }

                    // 删除按钮
                    ToolButton {
                        implicitWidth: 24
                        implicitHeight: 24
                        contentItem: Text {
                            text: "✕"
                            color: "#ff6b6b"
                            font.pixelSize: 14
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            color: parent.hovered ? hoverColor : "transparent"
                            radius: 4
                        }
                        onClicked: {
                            HistoryController.deleteHistoryItem(modelData.id)
                            refresh()
                        }
                    }
                }

                // 点击打开
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        HistoryController.loadHistoryItem(modelData.id)
                    }
                }
            }
        }
    }

    // 初始化加载
    Component.onCompleted: refresh()
}
