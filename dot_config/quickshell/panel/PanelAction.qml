import QtQuick
import QtQuick.Controls

Button {
    id: control
    padding: 8
    leftPadding: 12
    rightPadding: 12
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    contentItem: Text {
        text: control.text
        color: control.enabled ? "#d5c8ac" : "#827c70"
        font.family: "JetBrains Mono"
        font.pixelSize: 11
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 5
        color: control.down ? "#49453d" : control.hovered ? "#39362f" : "#302e29"
        border.color: control.visualFocus ? "#afa286" : "#49453d"
    }
}
