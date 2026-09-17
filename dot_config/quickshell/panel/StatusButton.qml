import QtQuick

Rectangle {
    id: button
    property string label: ""
    property color ink: "#afa286"
    signal activated(int mouseButton)
    signal scrolled(real delta)
    implicitWidth: caption.implicitWidth + 20
    implicitHeight: 38
    color: pointer.containsMouse ? "#39362f" : "transparent"
    Text {
        id: caption
        anchors.centerIn: parent
        text: button.label
        color: pointer.containsMouse ? "#d5c8ac" : button.ink
        font.family: "JetBrains Mono"
        font.pixelSize: 12
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: mouse => button.activated(mouse.button)
        onWheel: wheel => {
            button.scrolled(wheel.angleDelta.y);
            wheel.accepted = true;
        }
    }
}
