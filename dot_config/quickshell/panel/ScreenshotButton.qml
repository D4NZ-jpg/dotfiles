import QtQuick
import QtQuick.Controls

// Toolbar button: a line-art glyph (screen, window, region, close) or a text label.
AbstractButton {
    id: control
    property string glyph: ""
    property bool selected: false
    property bool emphasized: false
    property bool chevron: false
    readonly property color ink: "#d5c8ac"
    readonly property bool round: glyph === "close"
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    padding: 0
    implicitWidth: glyph !== "" ? (round ? 36 : 48) : label.implicitWidth + (chevron ? 34 : 24)
    implicitHeight: 36
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.checkable: glyph !== "" && !round
    Accessible.checked: selected
    background: Rectangle {
        radius: control.round ? height / 2 : 8
        color: Qt.rgba(0.835, 0.784, 0.675, control.down ? 0.22 : control.selected ? 0.16 : control.hovered ? 0.09 : control.round ? 0.06 : 0)
        border.width: control.visualFocus ? 1 : 0
        border.color: Qt.rgba(0.835, 0.784, 0.675, 0.6)
    }
    contentItem: Item {
        Canvas {
            id: art
            visible: control.glyph !== ""
            anchors.centerIn: parent
            width: 26; height: 20
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                ctx.strokeStyle = control.ink;
                ctx.fillStyle = control.ink;
                ctx.lineWidth = 1.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                if (control.glyph === "screen") {
                    ctx.beginPath(); ctx.roundedRect(3.75, 2.75, 18.5, 12.5, 2, 2); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(13, 15.5); ctx.lineTo(13, 18); ctx.moveTo(9.5, 18.25); ctx.lineTo(16.5, 18.25); ctx.stroke();
                } else if (control.glyph === "window") {
                    ctx.beginPath(); ctx.roundedRect(3.75, 3.25, 18.5, 13.5, 2.5, 2.5); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(3.75, 7.6); ctx.lineTo(22.25, 7.6); ctx.stroke();
                    for (const x of [6.6, 9.1, 11.6]) { ctx.beginPath(); ctx.arc(x, 5.3, 0.95, 0, 2 * Math.PI); ctx.fill(); }
                } else if (control.glyph === "region") {
                    ctx.setLineDash([1.6, 1.8]);
                    ctx.beginPath(); ctx.rect(3.75, 3.25, 18.5, 13.5); ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.beginPath(); ctx.roundedRect(15.5, 11, 5, 4, 1, 1); ctx.fill();
                } else if (control.glyph === "close") {
                    ctx.beginPath(); ctx.moveTo(9.25, 6.25); ctx.lineTo(16.75, 13.75); ctx.moveTo(16.75, 6.25); ctx.lineTo(9.25, 13.75); ctx.stroke();
                }
            }
            Connections { target: control; function onGlyphChanged() { art.requestPaint(); } }
        }
        Row {
            visible: control.glyph === ""
            anchors.centerIn: parent
            spacing: 6
            Text {
                id: label
                text: control.text
                color: control.ink
                font.family: "Noto Sans"
                font.pixelSize: 13
                font.weight: control.emphasized ? Font.DemiBold : Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }
            Canvas {
                visible: control.chevron
                width: 9; height: 6
                anchors.verticalCenter: parent.verticalCenter
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    ctx.strokeStyle = control.ink;
                    ctx.lineWidth = 1.5;
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.beginPath(); ctx.moveTo(1, 1); ctx.lineTo(4.5, 4.5); ctx.lineTo(8, 1); ctx.stroke();
                }
            }
        }
    }
}
