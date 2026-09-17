import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Networking

// The service can be replaced by a synthetic model in tests. No shell commands
// or password files are involved: connection requests go to NetworkManager.
Item {
    id: menu
    property var service: Networking
    property bool scanning: false
    property var pendingNetwork: null
    property bool busy: false
    property bool needsPassword: false
    property string message: ""
    property bool error: false
    signal dismissed()
    readonly property bool available: service.backend !== NetworkBackendType.None
    readonly property bool hasWifi: service.devices.values.some(d => d.type === DeviceType.Wifi)
    // Only shown when something needs attention; a healthy connection is
    // already visible in the bar.
    readonly property string connectivity: {
        if (!available) return "NetworkManager is unavailable";
        switch (service.connectivity) {
        case NetworkConnectivity.Portal: return "Sign-in required in your browser";
        case NetworkConnectivity.Limited: return "Connected · internet access is limited";
        case NetworkConnectivity.None: return "No internet connection";
        default: return "";
        }
    }
    implicitWidth: 380
    // Repeater rows are not laid out until the window is mapped, so the
    // pre-map height is computed from the device and network lists. Keep the
    // constants in sync with the delegates below.
    implicitHeight: Math.min(480, fixedHeight + Math.max(60, listHeight + 4))
    readonly property int fixedHeight: (connectivity !== "" ? 15 + 12 : 0) + (hasWifi ? 31 + 12 : 0) + 1 + 12
        + (message !== "" ? 12 + 15 : 0) + (needsPassword ? 12 + 99 : 0)
    // networks.values is an ObjectModel snapshot; track its count through the
    // model's own change signal so the height updates when scans add rows.
    property int networkRevision: 0
    Instantiator {
        model: menu.service.devices.values
        delegate: Connections {
            required property var modelData
            // Synthetic models may use plain objects; only QObjects can be targets.
            target: typeof modelData.networks === "object" && modelData.networks.objectName !== undefined ? modelData.networks : null
            ignoreUnknownSignals: true
            function onValuesChanged() { menu.networkRevision++; }
        }
    }
    readonly property int listHeight: {
        const revision = networkRevision;
        let total = 0, sections = 0;
        for (const device of service.devices.values) {
            const wifi = device.type === DeviceType.Wifi;
            let h = 12; // device title
            if (!device.nmManaged || (!wifi && !device.hasLink)) h += 6 + 15;
            const count = (!wifi || service.wifiEnabled) ? device.networks.values.length : 0;
            if (wifi && service.wifiEnabled && count === 0) h += 6 + 15;
            h += count * (6 + 65);
            total += h;
            sections++;
        }
        if (available && sections === 0) total += 15;
        return total + Math.max(0, sections - 1) * 12;
    }
    readonly property int layoutWidth: width > 0 ? width : implicitWidth
    focus: true
    Keys.onEscapePressed: dismissed()

    function supportsPassword(network) {
        return network.security === WifiSecurityType.WpaPsk
            || network.security === WifiSecurityType.Wpa2Psk
            || network.security === WifiSecurityType.Sae;
    }
    function clearPrompt() {
        password.text = "";
        needsPassword = false;
    }
    function fail(text) {
        timeout.stop();
        busy = false;
        message = text;
        error = true;
    }
    function connectNetwork(network) {
        if (busy || !network || network.stateChanging) return;
        clearPrompt();
        pendingNetwork = network;
        error = false;
        if (network.device.type === DeviceType.Wifi && !network.known
                && !supportsPassword(network)
                && network.security !== WifiSecurityType.Open
                && network.security !== WifiSecurityType.Owe) {
            fail("This security type needs a configured NetworkManager profile.");
            return;
        }
        busy = true;
        message = "Connecting…";
        timeout.restart();
        // Try stored credentials first. NoSecrets opens the password prompt.
        network.connect();
    }
    function submitPassword() {
        if (!pendingNetwork || busy || !needsPassword || password.text.length === 0) return;
        const secret = password.text;
        clearPrompt();
        error = false;
        busy = true;
        message = "Connecting…";
        timeout.restart();
        pendingNetwork.connectWithPsk(secret);
    }
    function connectionFailed(reason) {
        if (!pendingNetwork) return;
        clearPrompt();
        if (reason === ConnectionFailReason.NoSecrets && supportsPassword(pendingNetwork)) {
            fail("Enter the Wi-Fi password. If you already entered one, check it and retry.");
            needsPassword = true;
            Qt.callLater(() => password.forceActiveFocus());
        } else {
            const messages = {};
            messages[ConnectionFailReason.NoSecrets] = "Credentials are required. Configure this connection in NetworkManager.";
            messages[ConnectionFailReason.WifiAuthTimeout] = "Authentication timed out. Check the network and try again.";
            messages[ConnectionFailReason.WifiNetworkLost] = "The network is no longer in range.";
            messages[ConnectionFailReason.WifiClientDisconnected] = "The connection was interrupted.";
            messages[ConnectionFailReason.WifiClientFailed] = "Wi-Fi could not connect. Try again.";
            fail(messages[reason] || "Could not connect. Check NetworkManager and try again.");
        }
    }
    function cancelPrompt() {
        clearPrompt();
        pendingNetwork = null;
        message = "";
        error = false;
    }
    function shutdown() {
        clearPrompt();
        timeout.stop();
        pendingNetwork = null;
        busy = false;
    }
    Component.onDestruction: shutdown()
    Timer {
        id: timeout
        interval: 60000
        onTriggered: menu.fail("The connection is taking longer than expected. Check its status before retrying.")
    }
    Connections {
        target: menu.pendingNetwork
        function onConnectionFailed(reason) { menu.connectionFailed(reason); }
        function onConnectedChanged() {
            if (menu.pendingNetwork && menu.pendingNetwork.connected) {
                timeout.stop();
                menu.clearPrompt();
                menu.busy = false;
                menu.error = false;
                menu.message = "Connected";
            }
        }
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        spacing: 12
        Text {
            visible: menu.connectivity !== ""
            text: menu.connectivity
            color: "#d9b090"; font.family: "JetBrains Mono"; font.pixelSize: 11
            Layout.fillWidth: true; wrapMode: Text.Wrap
        }
        RowLayout {
            visible: menu.hasWifi
            Layout.fillWidth: true
            Text {
                text: !menu.service.wifiHardwareEnabled ? "Wi-Fi · hardware blocked" : menu.service.wifiEnabled ? "Wi-Fi enabled" : "Wi-Fi disabled"
                color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 12
                Layout.fillWidth: true
            }
            PanelAction {
                text: menu.service.wifiEnabled ? "Turn off" : "Turn on"
                enabled: menu.available && menu.service.wifiHardwareEnabled && !menu.busy
                onClicked: { menu.cancelPrompt(); menu.service.wifiEnabled = !menu.service.wifiEnabled; }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#49453d" }
        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: list.implicitHeight
            Layout.minimumHeight: 60
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            Column {
                id: list
                width: menu.layoutWidth
                spacing: 12
                Repeater {
                    model: menu.service.devices.values
                    delegate: Column {
                        id: deviceSection
                        required property var modelData
                        readonly property var device: modelData
                        readonly property bool wifi: device.type === DeviceType.Wifi
                        width: parent.width
                        spacing: 6
                        // Scan only while this menu is open; the destroyed loader
                        // cannot rely on Binding restoration, so stop explicitly.
                        property bool scanningHere: deviceSection.wifi && menu.scanning && menu.service.wifiEnabled
                        onScanningHereChanged: if (deviceSection.wifi) deviceSection.device.scannerEnabled = scanningHere
                        Component.onCompleted: if (deviceSection.wifi && scanningHere) deviceSection.device.scannerEnabled = true
                        Component.onDestruction: if (deviceSection.wifi) deviceSection.device.scannerEnabled = false
                        Text {
                            width: parent.width
                            text: (deviceSection.wifi ? "WI-FI" : "ETHERNET") + " · " + deviceSection.device.name
                            color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Text {
                            visible: !deviceSection.device.nmManaged || (!deviceSection.wifi && !deviceSection.device.hasLink)
                            text: !deviceSection.device.nmManaged ? "Not managed by NetworkManager" : "Cable unplugged"
                            color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
                        }
                        Text {
                            visible: deviceSection.wifi && menu.service.wifiEnabled && deviceSection.device.networks.values.length === 0
                            text: "Looking for nearby networks…"
                            color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
                        }
                        Repeater {
                            model: (!deviceSection.wifi || menu.service.wifiEnabled)
                                ? deviceSection.device.networks.values.slice().sort((a, b) =>
                                    Number(b.connected) - Number(a.connected)
                                    || Number(b.known) - Number(a.known)
                                    || (b.signalStrength || 0) - (a.signalStrength || 0)
                                    || a.name.localeCompare(b.name)) : []
                            delegate: Rectangle {
                                id: networkRow
                                required property var modelData
                                readonly property var network: modelData
                                width: deviceSection.width
                                height: 65
                                radius: 6
                                color: network.connected ? "#39362f" : "#2d2c29"
                                border.color: network.connected ? "#afa286" : "#49453d"
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 10
                                    spacing: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 5
                                        Text {
                                            text: networkRow.network.name || (deviceSection.wifi ? "Hidden network" : "Wired connection")
                                            textFormat: Text.PlainText
                                            color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 12
                                            Layout.fillWidth: true; elide: Text.ElideRight
                                        }
                                        Text {
                                            text: {
                                                const n = networkRow.network;
                                                let status = n.connected ? "Connected" : n.stateChanging ? ConnectionState.toString(n.state) : n.known ? "Saved" : "Available";
                                                if (deviceSection.wifi) status += " · " + Math.round(n.signalStrength * 100) + "% · "
                                                    + (n.security === WifiSecurityType.Open ? "Open" : WifiSecurityType.toString(n.security));
                                                return status;
                                            }
                                            color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 10
                                            Layout.fillWidth: true; elide: Text.ElideRight
                                        }
                                    }
                                    PanelAction {
                                        text: networkRow.network.connected ? "Disconnect" : "Connect"
                                        enabled: deviceSection.device.nmManaged && !menu.busy && !networkRow.network.stateChanging
                                            && (deviceSection.wifi || deviceSection.device.hasLink)
                                        onClicked: {
                                            if (networkRow.network.connected) {
                                                menu.cancelPrompt();
                                                networkRow.network.disconnect();
                                            } else menu.connectNetwork(networkRow.network);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    visible: menu.available && menu.service.devices.values.length === 0
                    text: "No supported network adapters found"
                    color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
                }
            }
        }
        Text {
            visible: menu.message !== ""
            text: menu.message; textFormat: Text.PlainText
            color: menu.error ? "#d9b090" : "#afa286"
            font.family: "JetBrains Mono"; font.pixelSize: 11
            Layout.fillWidth: true; wrapMode: Text.Wrap
            Accessible.role: Accessible.StaticText
            Accessible.name: text
        }
        ColumnLayout {
            visible: menu.needsPassword
            Layout.fillWidth: true
            spacing: 8
            Text {
                text: menu.pendingNetwork ? "Password for " + menu.pendingNetwork.name : "Wi-Fi password"
                textFormat: Text.PlainText
                color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 11
                Layout.fillWidth: true; elide: Text.ElideRight
            }
            TextField {
                id: password
                objectName: "networkPassword"
                Layout.fillWidth: true
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhHiddenText
                selectByMouse: true
                placeholderText: "Wi-Fi password"
                color: "#d5c8ac"; placeholderTextColor: "#827c70"
                selectionColor: "#afa286"; selectedTextColor: "#262626"
                font.family: "JetBrains Mono"; font.pixelSize: 12
                padding: 10
                background: Rectangle { color: "#222222"; radius: 5; border.color: password.activeFocus ? "#afa286" : "#49453d" }
                Accessible.name: "Wi-Fi password"
                onAccepted: menu.submitPassword()
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                PanelAction { text: "Cancel"; onClicked: menu.cancelPrompt() }
                PanelAction { text: "Connect"; enabled: password.text.length > 0 && !menu.busy; onClicked: menu.submitPassword() }
            }
        }
    }
}
