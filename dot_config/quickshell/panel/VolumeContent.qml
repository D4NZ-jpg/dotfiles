import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Services.Pipewire

// Output/input devices with volume, mute and default selection, plus
// per-application streams. `service` can be replaced by a synthetic model.
Item {
    id: menu
    property var service: Pipewire
    signal dismissed()
    // Width is fixed so the layout's height does not depend on the window
    // it sizes; a two-way dependency leaves the surface and buffer mismatched.
    implicitWidth: 380
    // Repeater delegates only get laid out once the item is inside a mapped
    // window, so the pre-map height is computed from the node lists. Rows
    // and titles have fixed heights; keep these in sync with the components.
    readonly property int rowHeight: 57
    readonly property int titleHeight: 14
    readonly property int gap: 14
    implicitHeight: {
        const parts = [];
        if (!service.ready) parts.push(15);
        parts.push(titleHeight);
        for (let i = 0; i < sinks.length; i++) parts.push(rowHeight);
        if (sinks.length === 0) parts.push(15);
        if (sources.length > 0) { parts.push(titleHeight); for (let i = 0; i < sources.length; i++) parts.push(rowHeight); }
        if (streams.length > 0) { parts.push(titleHeight); for (let i = 0; i < streams.length; i++) parts.push(rowHeight); }
        return parts.reduce((a, b) => a + b, 0) + gap * (parts.length - 1) + 4;
    }
    readonly property int layoutWidth: width > 0 ? width : implicitWidth
    focus: true
    Keys.onEscapePressed: dismissed()

    function label(node) {
        if (!node) return "";
        const app = node.properties ? node.properties["application.name"] : undefined;
        if (node.isStream && app) {
            const media = node.properties["media.name"];
            return media && media !== app ? app + " · " + media : app;
        }
        return node.description || node.nickname || node.name;
    }
    // Bind every audio node while open so volume/mute properties are live;
    // unbound nodes never become ready.
    readonly property var audioNodes: service.nodes.values.filter(n => (n.type & PwNodeType.Audio) && n.audio)
    PwObjectTracker { objects: menu.audioNodes }
    function nodesOf(kind) {
        return audioNodes.filter(n => {
            if (!n.ready) return false;
            if (kind === "stream") return n.isStream;
            if (n.isStream) return false;
            return kind === "sink" ? n.isSink : !n.isSink;
        });
    }
    readonly property var sinks: nodesOf("sink")
    readonly property var sources: nodesOf("source")
    readonly property var streams: nodesOf("stream")

    component NodeRow: ColumnLayout {
        id: row
        required property var modelData
        readonly property var node: modelData
        property bool selectable: false
        property bool selected: false
        signal choose()
        readonly property var audio: node.audio
        Layout.fillWidth: true
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            // Dot and name form one target for choosing the default device.
            Item {
                Layout.fillWidth: true
                implicitHeight: chooser.implicitHeight
                RowLayout {
                    id: chooser
                    anchors.fill: parent
                    spacing: 8
                    Rectangle {
                        visible: row.selectable
                        width: 8; height: 8; radius: 4
                        color: row.selected ? "#afa286" : "transparent"
                        border.color: "#afa286"
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Text {
                        text: menu.label(row.node)
                        textFormat: Text.PlainText
                        color: "#d5c8ac"; font.family: "JetBrains Mono"; font.pixelSize: 12
                        Layout.fillWidth: true; elide: Text.ElideRight
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: row.selectable && !row.selected
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: row.choose()
                }
            }
            Text {
                text: row.audio ? Math.round(row.audio.volume * 100) + "%" : "—"
                color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
            }
            PanelAction {
                text: row.audio && row.audio.muted ? "Unmute" : "Mute"
                enabled: !!row.audio
                onClicked: row.audio.muted = !row.audio.muted
            }
        }
        Slider {
            id: slider
            objectName: "volumeSlider"
            Layout.fillWidth: true
            // Custom background/handle give the control no implicit size;
            // without this the slider is zero height and unclickable.
            implicitHeight: 20
            Layout.preferredHeight: 20
            // PipeWire permits gain above 100%; keep it reachable but reversible.
            from: 0; to: 1.5; stepSize: 0.01
            enabled: !!row.audio
            value: row.audio ? row.audio.volume : 0
            onMoved: if (row.audio) row.audio.volume = value
            Accessible.name: menu.label(row.node) + " volume"
            background: Rectangle {
                x: slider.leftPadding; y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: slider.availableWidth; height: 4; radius: 2
                color: "#39362f"
                Rectangle {
                    width: slider.visualPosition * parent.width; height: parent.height; radius: 2
                    color: row.audio && row.audio.muted ? "#827c70" : "#afa286"
                }
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: 14; height: 14; radius: 7
                color: slider.pressed ? "#d5c8ac" : "#afa286"
                border.color: "#262626"
            }
        }
    }
    component SectionTitle: Text {
        Layout.fillWidth: true
        color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 10
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
        ColumnLayout {
            id: layout
            width: menu.layoutWidth
            spacing: 14
            Text {
                visible: !menu.service.ready
                text: "PipeWire is not available"
                color: "#d9b090"; font.family: "JetBrains Mono"; font.pixelSize: 11
            }
            SectionTitle { text: "OUTPUT" }
            Repeater {
                model: menu.sinks
                delegate: NodeRow {
                    selectable: menu.sinks.length > 1
                    selected: menu.service.defaultAudioSink === node
                    onChoose: menu.service.preferredDefaultAudioSink = node
                }
            }
            Text {
                visible: menu.sinks.length === 0
                text: "No output devices"
                color: "#afa286"; font.family: "JetBrains Mono"; font.pixelSize: 11
            }
            SectionTitle { text: "INPUT"; visible: menu.sources.length > 0 }
            Repeater {
                model: menu.sources
                delegate: NodeRow {
                    selectable: menu.sources.length > 1
                    selected: menu.service.defaultAudioSource === node
                    onChoose: menu.service.preferredDefaultAudioSource = node
                }
            }
            SectionTitle { text: "APPLICATIONS"; visible: menu.streams.length > 0 }
            Repeater {
                model: menu.streams
                delegate: NodeRow {}
            }
        }
    }
}
