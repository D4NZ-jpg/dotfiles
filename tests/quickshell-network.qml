import QtQuick
import Quickshell
import Quickshell.Networking
import "panel" as Panel

// Run through quickshell-panel.py, which copies this fixture into a sandbox.
// All mutations target these fake objects, never the real Networking singleton.
ShellRoot {
    id: suite
    property int checks: 0
    function check(value, description) {
        if (!value) throw new Error(description);
        checks++;
    }
    function childNamed(parent, name) {
        if (parent.objectName === name) return parent;
        for (const child of parent.children || []) {
            const result = childNamed(child, name);
            if (result) return result;
        }
        return null;
    }
    QtObject {
        id: service
        property int backend: NetworkBackendType.NetworkManager
        property bool wifiEnabled: true
        property bool wifiHardwareEnabled: true
        property int connectivity: NetworkConnectivity.Full
        property var devices: ({values: [wifi]})
    }
    QtObject {
        id: wifi
        property int type: DeviceType.Wifi
        property string name: "test-wifi"
        property bool nmManaged: true
        property bool scannerEnabled: false
        property var networks: ({values: [network]})
    }
    QtObject {
        id: network
        property string name: "<b>Synthetic network</b>"
        property var device: wifi
        property bool connected: false
        property bool known: true
        property bool stateChanging: false
        property int state: ConnectionState.Disconnected
        property int security: WifiSecurityType.Wpa2Psk
        property real signalStrength: 0.75
        property int connectCount: 0
        property int passwordCount: 0
        property int disconnectCount: 0
        signal connectionFailed(int reason)
        function connect() { connectCount++; }
        function connectWithPsk(secret) {
            suite.check(secret === "synthetic-test-password", "Password handed to the native-style method unchanged");
            passwordCount++;
        }
        function disconnect() { disconnectCount++; }
    }
    Panel.NetworkContent { id: menu; service: service; width: 380; height: 480 }
    Timer {
        interval: 100
        running: true
        onTriggered: {
            try {
                const field = suite.childNamed(menu, "networkPassword");
                suite.check(field !== null, "Password field exists");
                suite.check(!wifi.scannerEnabled, "No scanning while hidden");
                menu.scanning = true;
                suite.check(wifi.scannerEnabled, "Scanning enabled while open");
                menu.scanning = false;
                suite.check(!wifi.scannerEnabled, "Scanner state restored on close");
                suite.check(menu.connectivity === "", "Healthy connectivity shows no banner");
                service.connectivity = NetworkConnectivity.Portal;
                suite.check(menu.connectivity.indexOf("Sign-in") === 0, "Captive portal text");
                service.backend = NetworkBackendType.None;
                suite.check(!menu.available, "Missing backend detected");
                service.backend = NetworkBackendType.NetworkManager;

                menu.connectNetwork(network);
                suite.check(network.connectCount === 1 && menu.busy && !menu.needsPassword, "Saved secrets attempted first");
                menu.connectNetwork(network);
                suite.check(network.connectCount === 1, "Duplicate request blocked while busy");
                network.connectionFailed(ConnectionFailReason.NoSecrets);
                suite.check(menu.needsPassword && !menu.busy, "Missing secrets show prompt");
                menu.submitPassword();
                suite.check(network.passwordCount === 0, "Empty password not submitted");
                field.text = "synthetic-test-password";
                menu.submitPassword();
                suite.check(network.passwordCount === 1 && field.text === "" && !menu.needsPassword && menu.busy, "Submission immediately clears field");
                network.connectionFailed(ConnectionFailReason.NoSecrets);
                suite.check(menu.needsPassword && field.text === "", "Wrong password prompts again without retaining it");
                field.text = "synthetic-test-password";
                menu.cancelPrompt();
                suite.check(field.text === "" && menu.pendingNetwork === null && !menu.needsPassword, "Cancel clears secrets and selection");

                network.known = false;
                network.security = WifiSecurityType.Wpa2Eap;
                menu.connectNetwork(network);
                suite.check(network.connectCount === 1 && menu.error && !menu.needsPassword, "New enterprise network is not sent to PSK flow");
                network.known = true;
                menu.connectNetwork(network);
                suite.check(network.connectCount === 2 && menu.busy, "Saved enterprise profile can connect");
                network.connectionFailed(ConnectionFailReason.NoSecrets);
                suite.check(menu.error && !menu.needsPassword, "Enterprise credentials need external configuration");
                network.known = false;
                network.security = WifiSecurityType.Open;
                menu.connectNetwork(network);
                suite.check(network.connectCount === 3, "Open network connects without password");
                network.connected = true;
                suite.check(!menu.busy && !menu.error && menu.message === "Connected", "Successful connection updates UI");
                network.connected = false;
                network.security = WifiSecurityType.Sae;
                menu.connectNetwork(network);
                network.connectionFailed(ConnectionFailReason.NoSecrets);
                suite.check(menu.needsPassword, "WPA3 SAE password supported");
                field.text = "synthetic-test-password";
                menu.shutdown();
                suite.check(field.text === "" && menu.pendingNetwork === null && !menu.busy, "Closing clears transient state");
                suite.check(network.disconnectCount === 0, "Opening and closing never disconnects");
                console.log("NETWORK_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("NETWORK_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
