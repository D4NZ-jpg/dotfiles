import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

// Bottom-center capture bar. The surface includes transparent room for the
// shadow and the Options menu; input is masked to the visible material, so
// clicks elsewhere reach the desktop and clear the focus grab.
PanelWindow {
    id: toolbar
    required property var barWindow
    property alias mode: content.mode
    property alias destination: content.destination
    signal captured(string mode, string destination)
    signal dismissed()
    screen: barWindow.screen
    anchors.bottom: true
    margins.bottom: 20
    implicitWidth: content.implicitWidth
    implicitHeight: content.implicitHeight
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "dan-screenshot"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    mask: Region {
        item: content.bar
        Region { item: content.menuOpen ? content.menu : null }
    }
    HyprlandFocusGrab {
        windows: [toolbar]
        active: toolbar.visible
        onCleared: toolbar.dismissed()
    }
    ScreenshotContent {
        id: content
        anchors.fill: parent
        onDismissed: toolbar.dismissed()
        onCaptured: (mode, destination) => {
            toolbar.visible = false;
            toolbar.captured(mode, destination);
        }
    }
}
