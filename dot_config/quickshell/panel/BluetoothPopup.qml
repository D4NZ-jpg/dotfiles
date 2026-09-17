import QtQuick

PanelPopup {
    id: popup
    layerNamespace: "dan-bluetooth"
    contentHeight: content.implicitHeight
    BluetoothContent {
        id: content
        anchors.fill: parent
        // Discover from creation so the nearby list is settled before mapping.
        scanning: !popup.closing
        onDismissed: popup.close()
    }
}
