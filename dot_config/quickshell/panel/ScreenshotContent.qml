import QtQuick
import QtQuick.Controls

// One-row capture bar with an Options menu above it. The transparent margin
// holds the shadow; the window masks input to `bar` and `menu`.
Item {
    id: content
    property string mode: "region"
    property string destination: "clipboard"
    property bool menuOpen: false
    readonly property alias bar: bar
    readonly property alias menu: menu
    readonly property int shadowPad: 28
    readonly property color ink: "#d5c8ac"
    readonly property var modes: [
        {glyph: "screen", label: "Capture entire screen"},
        {glyph: "window", label: "Capture selected window"},
        {glyph: "region", label: "Capture selected region"}
    ]
    readonly property var destinations: [
        {label: "Clipboard", value: "clipboard"},
        {label: "Screenshots folder", value: "folder"},
        {label: "Clipboard and folder", value: "both"}
    ]
    implicitWidth: bar.width + 2 * shadowPad
    implicitHeight: bar.height + menu.height + 8 + 2 * shadowPad
    signal captured(string mode, string destination)
    signal dismissed()

    function openMenu(fromKeyboard) {
        menuOpen = true;
        const index = destinations.findIndex(d => d.value === destination);
        menuRows.itemAt(Math.max(0, index)).forceActiveFocus(fromKeyboard ? Qt.TabFocusReason : Qt.MouseFocusReason);
    }
    function closeMenu() {
        if (!menuOpen) return;
        const restore = menu.activeFocus;
        menuOpen = false;
        if (restore) optionsButton.forceActiveFocus(Qt.TabFocusReason);
    }
    function choose(value) {
        destination = value;
        closeMenu();
    }
    function capture() {
        menuOpen = false;
        captured(mode, destination);
    }
    function activate() {
        const focused = content.Window.activeFocusItem;
        if (menuOpen && focused && focused.hasOwnProperty("menuValue")) choose(focused.menuValue);
        else capture();
    }
    function stepMode(delta) {
        const index = modes.findIndex(m => m.glyph === mode);
        mode = modes[(index + delta + modes.length) % modes.length].glyph;
    }
    function handleKey(key) {
        if (key === Qt.Key_Escape) { if (menuOpen) closeMenu(); else dismissed(); }
        else if (key === Qt.Key_Return || key === Qt.Key_Enter) activate();
        else if (key === Qt.Key_1) mode = "screen";
        else if (key === Qt.Key_2) mode = "window";
        else if (key === Qt.Key_3) mode = "region";
        else if (key === Qt.Key_Left && !menuOpen) stepMode(-1);
        else if (key === Qt.Key_Right && !menuOpen) stepMode(1);
        else if (key === Qt.Key_C) choose("clipboard");
        else if (key === Qt.Key_F) choose("folder");
        else if (key === Qt.Key_B) choose("both");
        else if (key === Qt.Key_O) { if (menuOpen) closeMenu(); else openMenu(true); }
        else return false;
        return true;
    }
    focus: true
    Keys.onPressed: event => { event.accepted = handleKey(event.key); }
    Component.onCompleted: forceActiveFocus()
    // Window shortcuts keep Enter/Escape working while a child button has focus.
    Shortcut { sequences: ["Return", "Enter"]; context: Qt.WindowShortcut; onActivated: content.activate() }
    Shortcut { sequence: "Escape"; context: Qt.WindowShortcut; onActivated: content.handleKey(Qt.Key_Escape) }

    // Translucent material over a soft stepped shadow (no shader effects, so it
    // renders the same on every backend). Hyprland blurs what shows through.
    component Material: Item {
        id: material
        property real radius: 14
        Repeater {
            model: 6
            Rectangle {
                required property int index
                readonly property real spread: 2 + index * 3
                x: -spread; y: -spread + 6
                width: material.width + 2 * spread; height: material.height + 2 * spread
                radius: material.radius + spread
                color: Qt.rgba(0, 0, 0, 0.055)
            }
        }
        Rectangle {
            anchors.fill: parent
            radius: material.radius
            color: Qt.rgba(0.149, 0.149, 0.149, 0.86)
            border.color: Qt.rgba(0.835, 0.784, 0.675, 0.14)
        }
    }
    component Divider: Item {
        width: 13; height: 36
        Rectangle { anchors.centerIn: parent; width: 1; height: 22; color: Qt.rgba(0.835, 0.784, 0.675, 0.16) }
    }

    Item {
        id: bar
        width: controls.implicitWidth + 16
        height: 52
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: content.shadowPad
        Material { anchors.fill: parent }
        TapHandler { onTapped: content.closeMenu() }
        Row {
            id: controls
            anchors.centerIn: parent
            spacing: 2
            ScreenshotButton {
                glyph: "close"
                text: "Close"
                onClicked: content.dismissed()
            }
            Divider {}
            Repeater {
                model: content.modes
                ScreenshotButton {
                    required property var modelData
                    glyph: modelData.glyph
                    text: modelData.label
                    selected: content.mode === modelData.glyph
                    onClicked: { content.closeMenu(); content.mode = modelData.glyph; }
                }
            }
            Divider {}
            ScreenshotButton {
                id: optionsButton
                text: "Options"
                chevron: true
                selected: content.menuOpen
                onClicked: content.menuOpen ? content.closeMenu() : content.openMenu(false)
            }
            Divider {}
            ScreenshotButton {
                text: "Capture"
                emphasized: true
                onClicked: content.capture()
            }
        }
    }

    Item {
        id: menu
        visible: content.menuOpen
        width: 220
        height: menuColumn.implicitHeight + 12
        x: Math.max(content.shadowPad, Math.min(content.width - content.shadowPad - width,
            bar.x + controls.x + optionsButton.x + optionsButton.width / 2 - width / 2))
        anchors.bottom: bar.top
        anchors.bottomMargin: 8
        Material { anchors.fill: parent; radius: 12 }
        Column {
            id: menuColumn
            x: 6; y: 6
            width: parent.width - 12
            Text {
                text: "Save to"
                leftPadding: 10
                height: 26
                verticalAlignment: Text.AlignVCenter
                color: "#afa286"; font.family: "Noto Sans"; font.pixelSize: 11; font.weight: Font.Medium
            }
            Repeater {
                id: menuRows
                model: content.destinations
                AbstractButton {
                    id: option
                    required property var modelData
                    required property int index
                    readonly property string menuValue: modelData.value
                    readonly property bool current: content.destination === menuValue
                    text: modelData.label
                    width: menuColumn.width
                    implicitHeight: 30
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: text
                    Accessible.checked: current
                    onClicked: content.choose(menuValue)
                    Keys.onUpPressed: menuRows.itemAt((index + menuRows.count - 1) % menuRows.count).forceActiveFocus(Qt.TabFocusReason)
                    Keys.onDownPressed: menuRows.itemAt((index + 1) % menuRows.count).forceActiveFocus(Qt.TabFocusReason)
                    background: Rectangle {
                        radius: 7
                        color: Qt.rgba(0.835, 0.784, 0.675, option.down ? 0.2 : option.hovered || option.activeFocus ? 0.11 : 0)
                    }
                    contentItem: Item {
                        Text {
                            x: 10; anchors.verticalCenter: parent.verticalCenter
                            text: option.current ? "✓" : ""
                            color: content.ink; font.family: "Noto Sans"; font.pixelSize: 12
                        }
                        Text {
                            x: 28; anchors.verticalCenter: parent.verticalCenter
                            text: option.text
                            color: content.ink; font.family: "Noto Sans"; font.pixelSize: 13
                        }
                    }
                }
            }
        }
    }
}
