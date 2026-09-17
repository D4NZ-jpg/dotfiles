import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Bluetooth

// Adapter power, discovery while open, and paired/nearby devices with
// connect, disconnect, pair and forget. `service` can be a synthetic model.
Item {
    id: menu
    property var service: Bluetooth
    property bool scanning: false
    property string message: ""
    property bool error: false
    signal dismissed()
    readonly property var adapter: service.defaultAdapter
    readonly property bool powered: !!adapter && adapter.enabled && adapter.state === BluetoothAdapterState.Enabled
    readonly property bool busy: !!adapter && (adapter.state === BluetoothAdapterState.Enabling || adapter.state === BluetoothAdapterState.Disabling)
    implicitWidth: 380
    focus: true
    Keys.onEscapePressed: dismissed()

    function label(device) { return device.name || device.deviceName || device.address; }
    // BlueZ reports the address as the name for devices that never sent one.
    function named(device) {
        const n = device.name || device.deviceName || "";
        return n !== "" && n.replace(/-/g, ":") !== device.address;
    }
    function status(device) {
        if (device.pairing) return "Pairing…";
        switch (device.state) {
        case BluetoothDeviceState.Connected: return "Connected";
        case BluetoothDeviceState.Connecting: return "Connecting…";
        case BluetoothDeviceState.Disconnecting: return "Disconnecting…";
        }
        return device.paired ? "Paired" : "Available";
    }
    function detail(device) {
        let text = status(device);
        if (device.batteryAvailable) text += " · " + Math.round(device.battery * 100) + "%";
        return text;
    }
    function sorted(list) {
        return list.slice().sort((a, b) =>
            Number(b.connected) - Number(a.connected)
            || Number(b.paired) - Number(a.paired)
            || label(a).localeCompare(label(b)));
    }
    readonly property var paired: adapter ? sorted(adapter.devices.values.filter(d => d.paired || d.connected)) : []
    // Nameless advertisers are noise; hide them until they announce a name.
    readonly property var nearby: adapter && powered ? sorted(adapter.devices.values.filter(d => !d.paired && !d.connected && named(d))) : []
    function act(device, action) {
        message = "";
        error = false;
        try { action(); } catch (e) { message = "Bluetooth request failed: " + e; error = true; }
    }
    // Discovery only while this menu is open; stop explicitly on close.
    // BlueZ rejects repeated start/stop calls and the adapter property does
    // not confirm them, so track what this menu itself requested.
    readonly property bool discover: scanning && powered
    property bool requestedDiscovery: false
    function syncDiscovery(want) {
        if (!adapter || want === requestedDiscovery) return;
        requestedDiscovery = want;
        if (adapter.discovering !== want) adapter.discovering = want;
    }
    onDiscoverChanged: syncDiscovery(discover)
    Component.onCompleted: syncDiscovery(discover)
    Component.onDestruction: syncDiscovery(false)

    // Pre-map height from the lists; keep constants in sync with the delegates.
    readonly property int rowHeight: 65
    readonly property int titleHeight: 14
    readonly property int gap: 12
    // Nearby devices trickle in for seconds after discovery starts, so that
    // section has a fixed height and scrolls internally; the surface itself
    // never resizes after mapping. Paired devices are known up front.
    readonly property int nearbyHeight: 2 * (rowHeight + gap) - gap
    implicitHeight: {
        const parts = [31];
        if (!adapter) parts.push(15);
        else if (powered) {
            parts.push(titleHeight + 6 + (paired.length ? paired.length * (rowHeight + gap) - gap : 15));
            parts.push(titleHeight + 6 + nearbyHeight);
        }
        parts.push(15); // message line is always reserved
        return parts.reduce((a, b) => a + b, 0) + gap * (parts.length - 1) + 4;
    }

    component DeviceRow: Rectangle {
        id: deviceRow
        required property var modelData
        readonly property var device: modelData
        width: parent.width
        height: menu.rowHeight
        radius: 6
        color: device.connected ? "#39362f" : "#2d2c29"
        border.color: device.connected ? "#afa286" : "#49453d"
        RowLayout {
            anchors.fill: parent; anchors.margins: 10
            spacing: 8
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5
                Text {
                    text: menu.label(deviceRow.device)
                    textFormat: Text.PlainText
                    color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 12
                    Layout.fillWidth: true; elide: Text.ElideRight
                }
                Text {
                    text: menu.detail(deviceRow.device)
                    color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 10
                    Layout.fillWidth: true; elide: Text.ElideRight
                }
            }
            PanelAction {
                visible: deviceRow.device.paired
                text: "Forget"
                enabled: !deviceRow.device.pairing && deviceRow.device.state === BluetoothDeviceState.Disconnected
                onClicked: menu.act(deviceRow.device, () => deviceRow.device.forget())
            }
            PanelAction {
                text: deviceRow.device.pairing ? "Cancel"
                    : deviceRow.device.connected ? "Disconnect"
                    : deviceRow.device.paired ? "Connect" : "Pair"
                enabled: deviceRow.device.pairing
                    || deviceRow.device.state === BluetoothDeviceState.Connected
                    || deviceRow.device.state === BluetoothDeviceState.Disconnected
                onClicked: {
                    const d = deviceRow.device;
                    if (d.pairing) menu.act(d, () => d.cancelPair());
                    else if (d.connected) menu.act(d, () => d.disconnect());
                    else if (d.paired) menu.act(d, () => d.connect());
                    else {
                        menu.act(d, () => d.pair());
                        menu.message = "Pairing. Devices needing a PIN or confirmation must be paired in blueman-manager.";
                    }
                }
            }
        }
    }
    component SectionTitle: Text {
        width: parent.width
        color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 10
    }
    component Hint: Text {
        width: parent.width
        color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
        wrapMode: Text.Wrap
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: layout.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height
        ScrollBar.vertical: ScrollBar { policy: scroll.contentHeight > scroll.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
        Column {
            id: layout
            width: menu.width > 0 ? menu.width : menu.implicitWidth
            spacing: menu.gap
            RowLayout {
                width: parent.width
                Text {
                    text: !menu.adapter ? "No Bluetooth adapter"
                        : menu.adapter.state === BluetoothAdapterState.Blocked ? "Bluetooth blocked (rfkill)"
                        : menu.busy ? BluetoothAdapterState.toString(menu.adapter.state) + "…"
                        : menu.powered ? "Bluetooth on" : "Bluetooth off"
                    color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 12
                    Layout.fillWidth: true
                }
                PanelAction {
                    text: menu.powered ? "Turn off" : "Turn on"
                    enabled: !!menu.adapter && !menu.busy && menu.adapter.state !== BluetoothAdapterState.Blocked
                    onClicked: menu.act(null, () => menu.adapter.enabled = !menu.powered)
                }
            }
            Hint { visible: !menu.adapter; text: "Connect a Bluetooth adapter or unblock it with rfkill." }
            Column {
                visible: menu.powered
                width: parent.width
                spacing: 6
                SectionTitle { text: "PAIRED" }
                Repeater { model: menu.paired; delegate: DeviceRow {} }
                Hint { visible: menu.paired.length === 0; text: "No paired devices" }
            }
            Column {
                visible: menu.powered
                width: parent.width
                spacing: 6
                SectionTitle { text: menu.discover ? "NEARBY · scanning" : "NEARBY" }
                Flickable {
                    id: nearbyScroll
                    width: parent.width
                    height: menu.nearbyHeight
                    clip: true
                    contentWidth: width
                    contentHeight: nearbyList.height
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: contentHeight > height
                    ScrollBar.vertical: ScrollBar { policy: nearbyScroll.contentHeight > nearbyScroll.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
                    Column {
                        id: nearbyList
                        width: parent.width
                        spacing: menu.gap
                        Repeater { model: menu.nearby; delegate: DeviceRow {} }
                        Hint { visible: menu.nearby.length === 0; text: menu.discover ? "Looking for devices…" : "No devices found" }
                    }
                }
            }
            Text {
                width: parent.width
                text: menu.message; textFormat: Text.PlainText
                color: menu.error ? "#d9b090" : "#afa286"
                font.family: "JetBrains Mono"; font.pixelSize: 11
                wrapMode: Text.Wrap
            }
        }
    }
}
