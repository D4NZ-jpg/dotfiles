import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

// Shared shell for bar popups: small overlay under the bar's right edge,
// on-demand keyboard focus plus a Hyprland focus grab for outside-click and
// Escape dismissal. Exclusive focus would route all pointer input here and
// break outside clicks.
PanelWindow {
    id: popup
    required property var barWindow
    default property alias content: body.data
    property int contentHeight: 0
    property string layerNamespace: "dan-popup"
    signal dismissed()
    screen: barWindow.screen
    anchors { top: true; right: true }
    margins { top: 46; right: 20 }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: layerNamespace
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    implicitWidth: 412
    // Hyprland keeps stretching the first buffer when a layer surface grows
    // right after mapping, so the height is decided before the surface maps
    // and follows the content afterwards. Content must report its
    // implicitHeight without a layout pass (see the Content components).
    implicitHeight: Math.max(160, Math.min(contentHeight + 32, (screen ? screen.height : 900) - 80))
    color: "transparent"
    visible: settled && !closing
    property bool closing: false
    // Live services populate over the first frames (Wi-Fi scans start once
    // the content is created); map only after the height has been stable.
    property bool settled: false
    onContentHeightChanged: if (!settled) settle.restart()
    Timer {
        id: settle
        interval: 120
        running: !popup.settled
        onTriggered: if (popup.contentHeight > 0) popup.settled = true; else restart();
    }
    function close() { closing = true; }
    HyprlandFocusGrab {
        windows: [popup]
        active: popup.visible
        onCleared: popup.close()
    }
    onClosingChanged: if (closing) dismissed()
    Rectangle {
        anchors.fill: parent
        color: "#262626"
        radius: 9
        border.color: "#49453d"
        Item { id: body; anchors.fill: parent; anchors.margins: 16 }
    }
}
