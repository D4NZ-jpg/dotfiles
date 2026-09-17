import QtQuick

PanelPopup {
    id: popup
    layerNamespace: "dan-volume"
    contentHeight: content.implicitHeight
    VolumeContent {
        id: content
        anchors.fill: parent
        onDismissed: popup.close()
    }
}
