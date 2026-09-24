import QtQuick

PanelPopup {
    id: popup
    property var status: ({})
    signal refresh()
    layerNamespace: "dan-sync"
    contentHeight: content.implicitHeight
    SyncContent {
        id: content
        anchors.fill: parent
        status: popup.status
        onDismissed: popup.close()
        onRefresh: popup.refresh()
    }
}
