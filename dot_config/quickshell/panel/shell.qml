import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.Pipewire
import Quickshell.Bluetooth
import Quickshell.Networking

ShellRoot {
    id: root
    property bool overview: false
    property bool launcher: false
    property bool manual: false
    // At most one popup is open: `popup` names it, `popupMonitor` places it.
    property string popup: ""
    property string popupMonitor: ""
    readonly property bool forced: overview || launcher || manual || popup !== ""
    readonly property color ink: "#d5c8ac"
    readonly property color muted: "#afa286"
    readonly property string networkStatus: {
        if (Networking.backend === NetworkBackendType.None) return "NET —";
        let wired = false, wifi = false, connecting = false;
        for (const device of Networking.devices.values) {
            connecting = connecting || device.state === ConnectionState.Connecting;
            if (!device.connected) continue;
            if (device.type === DeviceType.Wired) wired = true;
            if (device.type === DeviceType.Wifi) wifi = true;
        }
        if (wired && wifi) return "ETH + WI-FI";
        if (wired) return "ETHERNET";
        if (wifi) return "WI-FI";
        return connecting ? "CONNECTING" : "DISCONNECTED";
    }

    // IPC accepts a monitor name, "focused" for the active Hyprland monitor,
    // or "" to close.
    function ipcPopup(name, monitor) {
        if (monitor === "focused") monitor = Hyprland.focusedMonitor?.name ?? "";
        if (monitor === "") closePopup();
        else if (Quickshell.screens.some(s => s.name === monitor)) togglePopup(name, monitor);
    }
    function closePopup() {
        popup = "";
        popupMonitor = "";
        overviewExit.popup = "";
        overviewExit.monitor = "";
    }
    function togglePopup(name, monitor) {
        const pending = overviewExit.running && overviewExit.popup === name && overviewExit.monitor === monitor;
        if ((popup === name && popupMonitor === monitor) || pending) {
            closePopup();
            return;
        }
        popup = "";
        popupMonitor = "";
        overviewExit.popup = name;
        overviewExit.monitor = monitor;
        if (!overviewExit.running) overviewExit.running = true;
    }
    onOverviewChanged: { if (overview) closePopup(); }
    onLauncherChanged: { if (launcher) closePopup(); }
    // Dismiss the overview before showing a popup so input is not contested.
    Process {
        id: overviewExit
        property string popup: ""
        property string monitor: ""
        command: ["hyprctl", "eval", "hl.plugin.scrolloverview._dispatch(\"overview\", \"off all\")"]
        onExited: {
            const name = popup, requested = monitor;
            popup = "";
            monitor = "";
            if (!root.launcher && name !== "" && Quickshell.screens.some(s => s.name === requested)) {
                root.popupMonitor = requested;
                root.popup = name;
            }
        }
    }
    SystemClock { id: clock; precision: SystemClock.Minutes }
    PwObjectTracker { objects: [Pipewire.defaultAudioSink] }
    IpcHandler {
        target: "panel"
        function preview(show: bool): void { root.manual = show; }
        function network(monitor: string): void { root.ipcPopup("network", monitor); }
        function volume(monitor: string): void { root.ipcPopup("volume", monitor); }
        function bluetooth(monitor: string): void { root.ipcPopup("bluetooth", monitor); }
        function status(): string {
            return JSON.stringify({overview: root.overview, launcher: root.launcher, manual: root.manual, network: root.networkStatus, popup: root.popup, popupMonitor: root.popupMonitor, networkScanning: Networking.devices.values.some(d => d.type === DeviceType.Wifi && d.scannerEnabled)});
        }
    }
    // Query actual layer state rather than keeping an open/close counter.
    Process {
        id: layers
        command: ["hyprctl", "-j", "layers"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const screens = JSON.parse(text);
                    let found = false;
                    for (const screen of Object.values(screens))
                        for (const list of Object.values(screen.levels || {}))
                            for (const surface of list)
                                if (/rofi/i.test(surface.namespace || "")) found = true;
                    root.launcher = found;
                } catch (e) { console.warn("Layer query failed:", e); }
            }
        }
    }
    Timer { id: layerRefresh; interval: 40; onTriggered: { if (!layers.running) layers.running = true; else restart(); } }
    Process {
        id: submap
        command: ["hyprctl", "submap"]
        stdout: StdioCollector { onStreamFinished: root.overview = text.trim() === "scrolloverview" }
    }
    Component.onCompleted: { layers.running = true; submap.running = true; }
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name === "submap") root.overview = event.data.trim() === "scrolloverview";
            if (event.name === "openlayer" || event.name === "closelayer") layerRefresh.restart();
            if (event.name === "configreloaded") {
                layerRefresh.restart();
                if (!submap.running) submap.running = true;
            }
        }
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: panel
            required property var modelData
            screen: modelData
            anchors { top: true; left: true; right: true }
            implicitHeight: 38
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: "dan-panel"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            Component.onDestruction: {
                if (root.popupMonitor === modelData.name) root.closePopup();
            }
            LazyLoader {
                active: root.popup === "network" && root.popupMonitor === panel.screen.name
                NetworkPopup { barWindow: panel; onDismissed: root.closePopup() }
            }
            LazyLoader {
                active: root.popup === "volume" && root.popupMonitor === panel.screen.name
                VolumePopup { barWindow: panel; onDismissed: root.closePopup() }
            }
            LazyLoader {
                active: root.popup === "bluetooth" && root.popupMonitor === panel.screen.name
                BluetoothPopup { barWindow: panel; onDismissed: root.closePopup() }
            }
            property bool hovered: false
            readonly property bool revealed: root.forced || hovered
            // Hidden panel only owns a two-pixel hover strip; everything else passes through.
            mask: Region { width: panel.width; height: Math.max(2, Math.ceil(bar.y + bar.height)) }
            Timer { id: showDelay; interval: 120; onTriggered: panel.hovered = true }
            Timer { id: hideDelay; interval: 280; onTriggered: panel.hovered = false }
            HoverHandler {
                onHoveredChanged: {
                    if (hovered) { hideDelay.stop(); if (!panel.revealed) showDelay.restart(); else panel.hovered = true; }
                    else { showDelay.stop(); hideDelay.restart(); }
                }
            }
            Rectangle {
                id: bar
                width: parent.width
                height: 38
                y: panel.revealed ? 0 : -height
                color: "#262626"
                Behavior on y {
                    NumberAnimation {
                        duration: 180
                        easing.type: Easing.BezierSpline
                        easing.bezierCurve: [0.23, 1, 0.32, 1, 1, 1]
                    }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#49453d" }
                Text {
                    anchors.centerIn: parent
                    text: Qt.formatDateTime(clock.date, "ddd  d MMM    HH:mm")
                    color: root.ink; font.family: "JetBrains Mono"; font.pixelSize: 12
                }
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    StatusButton {
                        label: root.networkStatus
                        onActivated: mouseButton => {
                            if (mouseButton === Qt.LeftButton) root.togglePopup("network", panel.screen.name);
                        }
                    }
                    StatusButton {
                        label: {
                            const audio = Pipewire.defaultAudioSink?.audio;
                            return !audio ? "VOL —" : audio.muted ? "MUTED" : "VOL " + Math.round(audio.volume * 100) + "%";
                        }
                        onActivated: mouseButton => {
                            if (mouseButton === Qt.LeftButton) root.togglePopup("volume", panel.screen.name);
                            else {
                                const audio = Pipewire.defaultAudioSink?.audio;
                                if (audio) audio.muted = !audio.muted;
                            }
                        }
                        onScrolled: delta => {
                            const audio = Pipewire.defaultAudioSink?.audio;
                            if (audio && delta !== 0) audio.volume = Math.max(0, Math.min(1, audio.volume + (delta > 0 ? 0.05 : -0.05)));
                        }
                    }
                    StatusButton {
                        label: Bluetooth.defaultAdapter?.enabled ? "BT ON" : "BT OFF"
                        onActivated: mouseButton => {
                            if (mouseButton === Qt.LeftButton) root.togglePopup("bluetooth", panel.screen.name);
                        }
                    }
                }
            }
        }
    }
}
