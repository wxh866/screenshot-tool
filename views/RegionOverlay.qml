// 区域截图覆盖层 - 全屏半透明遮罩 + 选区高亮
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Rectangle {
    id: overlayRoot
    color: "transparent"
    visible: true

    // 外部信号
    signal regionConfirmed(int x, int y, int width, int height)
    signal captureCancelled()

    // 背景图路径（由Python设置）
    property string backgroundPath: ""

    // 选区状态
    property bool isSelecting: false
    property int startX: 0
    property int startY: 0
    property int currentX: 0
    property int currentY: 0

    // 选区矩形（规范化后的）
    property int selX: Math.min(startX, currentX)
    property int selY: Math.min(startY, currentY)
    property int selW: Math.abs(currentX - startX)
    property int selH: Math.abs(currentY - startY)

    // 背景截图
    Image {
        id: backgroundImage
        anchors.fill: parent
        source: backgroundPath ? "file:///" + backgroundPath : ""
        fillMode: Image.Stretch
        cache: false
        z: 0
    }

    // 半透明遮罩层
    Canvas {
        id: maskCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            // 绘制背景图（模糊或暗化）
            ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
            ctx.fillRect(0, 0, width, height);

            // 如果有选区，清除选区内的遮罩
            if (isSelecting && selW > 0 && selH > 0) {
                ctx.clearRect(selX, selY, selW, selH);
            }
        }
    }

    // 选区边框和尺寸信息 Canvas
    Canvas {
        id: borderCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            if (!isSelecting || selW <= 0 || selH <= 0) return;

            // 选区边框 - 蓝色虚线
            ctx.strokeStyle = "#4A8CFF";
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 3]);
            ctx.strokeRect(selX, selY, selW, selH);
            ctx.setLineDash([]);

            // 半透明白色内边框（增强可见性）
            ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
            ctx.lineWidth = 1;
            ctx.strokeRect(selX + 1, selY + 1, selW - 2, selH - 2);

            // 选区尺寸显示（右下角）
            var sizeText = selW + " x " + selH;
            ctx.font = "bold 13px 'Microsoft YaHei', '微软雅黑', sans-serif";
            var textMetrics = ctx.measureText(sizeText);
            var textW = textMetrics.width + 12;
            var textH = 24;

            // 尺寸标签背景
            var labelX, labelY;
            if (selY + selH + textH + 16 > height) {
                // 选区底部空间不足，放选区内部右上角
                labelX = selX + selW - textW - 4;
                labelY = selY + 4;
            } else {
                // 放选区底部外侧
                labelX = selX + selW - textW;
                labelY = selY + selH + 8;
            }

            ctx.fillStyle = "#4A8CFF";
            ctx.beginPath();
            ctx.roundRect(labelX, labelY, textW, textH, 4);
            ctx.fill();

            ctx.fillStyle = "#FFFFFF";
            ctx.fillText(sizeText, labelX + 6, labelY + 17);
        }
    }

    // 辅助线 Canvas（十字准线）
    Canvas {
        id: guideCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            if (!isSelecting || selW <= 0 || selH <= 0) return;
            ctx.strokeStyle = "rgba(74, 140, 255, 0.15)";
            ctx.lineWidth = 1;

            // 水平中线 — 经过选区中心Y的水平线
            var midY = selY + selH / 2;
            ctx.beginPath();
            ctx.moveTo(0, midY);
            ctx.lineTo(width, midY);
            ctx.stroke();

            // 垂直中线 — 经过选区中心X的垂直线
            var midX = selX + selW / 2;
            ctx.beginPath();
            ctx.moveTo(midX, 0);
            ctx.lineTo(midX, height);
            ctx.stroke();
        }
    }

    // 鼠标区域 - 拖拽选区
    MouseArea {
        id: dragArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.CrossCursor

        onPressed: function(mouse) {
            isSelecting = true;
            startX = mouse.x;
            startY = mouse.y;
            currentX = mouse.x;
            currentY = mouse.y;
            maskCanvas.requestPaint();
            borderCanvas.requestPaint();
            guideCanvas.requestPaint();
        }

        onPositionChanged: function(mouse) {
            if (isSelecting) {
                currentX = mouse.x;
                currentY = mouse.y;
                maskCanvas.requestPaint();
                borderCanvas.requestPaint();
                guideCanvas.requestPaint();
            }
        }

        onReleased: function(mouse) {
            if (isSelecting) {
                isSelecting = false;
                currentX = mouse.x;
                currentY = mouse.y;
                maskCanvas.requestPaint();
                borderCanvas.requestPaint();
                guideCanvas.requestPaint();

                // 确认选区
                if (selW >= 5 && selH >= 5) {
                    regionConfirmed(selX, selY, selW, selH);
                } else {
                    captureCancelled();
                }
            }
        }
    }

    // 键盘事件
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
            captureCancelled();
            event.accepted = true;
        }
    }

    // 提示文字
    Text {
        anchors.centerIn: parent
        visible: !isSelecting
        text: "拖拽鼠标选择截图区域\n按 Esc 取消"
        font.pixelSize: 14
        font.family: "Microsoft YaHei, 微软雅黑"
        color: "#FFFFFF"
        opacity: 0.7
        horizontalAlignment: Text.AlignHCenter
        lineHeight: 1.6
    }

    Component.onCompleted: {
        forceActiveFocus();
    }
}
