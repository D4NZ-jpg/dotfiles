import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

PanelWindow {
    id: popup
    required property var barWindow
    screen: barWindow.screen
    anchors { top: true; right: true }
    margins { top: 46; right: 20 }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "dan-network"
    WlrLayershell.layer: WlrLayer.Overlay
    // Exclusive keyboard focus makes Hyprland route every pointer event to this
    // surface, so outside clicks never reach the focus grab. OnDemand lets the
    // grab hold keyboard focus and still see clicks elsewhere.
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    signal dismissed()
    implicitWidth: 412
    implicitHeight: Math.max(160, Math.min(content.implicitHeight + 32, (screen ? screen.height : 900) - 80))
    color: "transparent"
    visible: true
    // The grab dismisses the popup on outside clicks. Only the popup is listed:
    // with the bar included, Hyprland may give keyboard focus to the bar and
    // Escape never reaches this window.
    HyprlandFocusGrab {
        windows: [popup]
        active: popup.visible
        onCleared: popup.visible = false
    }
    onVisibleChanged: {
        if (!visible) {
            content.shutdown();
            dismissed();
        }
    }
    Rectangle {
        anchors.fill: parent
        color: "#262626"
        radius: 9
        border.color: "#49453d"
        NetworkContent {
            id: content
            anchors.fill: parent
            anchors.margins: 16
            scanning: popup.visible
            onDismissed: popup.visible = false
        }
    }
}
