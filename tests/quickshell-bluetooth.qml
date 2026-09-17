import QtQuick
import Quickshell
import Quickshell.Bluetooth
import "panel" as Panel

// Run through quickshell-panel.py. Fake adapter/devices stand in for BlueZ.
ShellRoot {
    id: suite
    property int checks: 0
    function check(value, description) {
        if (!value) throw new Error(description);
        checks++;
    }
    function findAll(parent, predicate, out) {
        out = out || [];
        if (predicate(parent)) out.push(parent);
        for (const child of parent.children || []) findAll(child, predicate, out);
        return out;
    }
    component FakeDevice: QtObject {
        property string address: "00:00:00:00:00:00"
        property string name: ""
        property string deviceName: ""
        property int state: BluetoothDeviceState.Disconnected
        property bool connected: false
        property bool paired: false
        property bool pairing: false
        property bool trusted: false
        property bool batteryAvailable: false
        property real battery: 0
        property var calls: []
        function connect() { calls.push("connect"); }
        function disconnect() { calls.push("disconnect"); }
        function pair() { calls.push("pair"); }
        function cancelPair() { calls.push("cancelPair"); }
        function forget() { calls.push("forget"); }
    }
    FakeDevice { id: headset; address: "AA:BB:CC:DD:EE:01"; name: "Headset"; paired: true; connected: true; state: BluetoothDeviceState.Connected; batteryAvailable: true; battery: 0.8 }
    FakeDevice { id: keyboard; address: "AA:BB:CC:DD:EE:02"; name: "Keyboard"; paired: true }
    FakeDevice { id: speaker; address: "AA:BB:CC:DD:EE:03"; name: "Speaker" }
    FakeDevice { id: anon; address: "AA:BB:CC:DD:EE:04"; name: "AA-BB-CC-DD-EE-04" }
    QtObject {
        id: adapter
        property bool enabled: true
        property int state: BluetoothAdapterState.Enabled
        property bool discovering: false
        property int discoveryWrites: 0
        onDiscoveringChanged: discoveryWrites++
        property var devices: ({values: [speaker, keyboard, headset, anon]})
    }
    QtObject { id: service; property var defaultAdapter: adapter }
    Panel.BluetoothContent { id: menu; service: service; width: 380; height: 600 }
    Timer {
        interval: 100
        running: true
        onTriggered: {
            try {
                suite.check(menu.paired.length === 2 && menu.paired[0] === headset, "Paired list sorted with connected first");
                suite.check(menu.nearby.length === 1 && menu.nearby[0] === speaker, "Nearby hides paired and nameless devices");
                suite.check(menu.detail(headset) === "Connected · 80%", "Battery shown for connected device");
                suite.check(menu.detail(keyboard) === "Paired", "Paired detail");
                suite.check(!adapter.discovering, "No discovery until scanning is requested");
                menu.scanning = true;
                suite.check(adapter.discovering && adapter.discoveryWrites === 1, "Scanning starts discovery once");
                menu.scanning = true;
                adapter.discovering = true;
                suite.check(adapter.discoveryWrites === 1, "Redundant scan requests do not rewrite discovery");
                menu.scanning = false;
                suite.check(!adapter.discovering, "Closing stops discovery");
                const buttons = suite.findAll(menu, o => o.hasOwnProperty("text") && o.hasOwnProperty("down"));
                const forHeadset = buttons.filter(b => b.text === "Disconnect");
                suite.check(forHeadset.length === 1, "Connected device offers Disconnect");
                forHeadset[0].clicked();
                suite.check(headset.calls.join() === "disconnect", "Disconnect calls the device");
                buttons.find(b => b.text === "Connect").clicked();
                suite.check(keyboard.calls.join() === "connect", "Connect calls the paired device");
                buttons.find(b => b.text === "Pair").clicked();
                suite.check(speaker.calls.join() === "pair" && !speaker.trusted, "Pair does not silently trust the device");
                suite.check(menu.message.indexOf("blueman") !== -1, "Pairing explains the authenticated-pairing limitation");
                const forgets = buttons.filter(b => b.text === "Forget" && b.visible);
                suite.check(forgets.length === 2, "Forget offered for paired devices only");
                suite.check(forgets.some(b => !b.enabled), "Forget disabled while connected");
                forgets.find(b => b.enabled).clicked();
                suite.check(keyboard.calls.join() === "connect,forget", "Forget calls the disconnected device");
                adapter.state = BluetoothAdapterState.Blocked;
                suite.check(!menu.powered, "Blocked adapter counts as unpowered");
                suite.check(headset.calls.length === 1 && speaker.calls.length === 1, "No additional device calls from rendering");
                console.log("BLUETOOTH_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("BLUETOOTH_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
