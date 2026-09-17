import QtQuick

PanelPopup {
    id: popup
    layerNamespace: "dan-network"
    contentHeight: content.implicitHeight
    onClosingChanged: if (closing) content.shutdown()
    NetworkContent {
        id: content
        anchors.fill: parent
        // Scan from creation, not from mapping: the popup waits for the list
        // to settle before it maps, so the first buffer already fits.
        scanning: !popup.closing
        onDismissed: popup.close()
    }
}
