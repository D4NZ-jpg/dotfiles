import QtQuick
import QtQuick.Layouts

// Handoff and Syncthing state at a glance. `status` is the object written by
// sync-status.py (see shell.qml); a synthetic one works for tests.
Item {
    id: menu
    property var status: ({})
    signal dismissed()
    signal refresh()

    readonly property color ink: "#d5c8ac"
    readonly property color muted: "#afa286"
    readonly property color dim: "#827c70"
    readonly property color warn: "#d9b090"
    readonly property color bad: "#c98a7a"
    readonly property color border: "#49453d"

    readonly property var handoff: status.handoff ?? ({})
    readonly property var incoming: status.incoming ?? []
    readonly property var syncthing: status.syncthing ?? ({ folders: [] })
    readonly property var folders: syncthing.folders ?? []
    // Show active/erroring folders; idle ones are collapsed into a count.
    readonly property var shownFolders: folders.filter(f => f.state !== "idle" && f.state !== "paused")
    readonly property int idleFolders: folders.filter(f => f.state === "idle").length
    readonly property int maxIncoming: 8

    implicitWidth: 380
    readonly property int rowHeight: 24
    readonly property int titleHeight: 26
    implicitHeight: {
        let h = 14 + rowHeight;                      // handoff line
        h += titleHeight + rowHeight * (shownFolders.length + 1); // syncthing block + summary line
        h += titleHeight + rowHeight * Math.max(1, Math.min(incoming.length, maxIncoming));
        if (incoming.length > maxIncoming) h += rowHeight;
        return h + 14;
    }
    readonly property int layoutWidth: width > 0 ? width : implicitWidth

    focus: true
    Keys.onEscapePressed: dismissed()
    Keys.onPressed: event => { if (event.key === Qt.Key_R) { refresh(); event.accepted = true; } }

    function ago(epoch) {
        if (!epoch) return "";
        const s = Math.floor(Date.now() / 1000 - epoch);
        if (s < 60) return "now";
        if (s < 3600) return Math.floor(s / 60) + "m";
        if (s < 86400) return Math.floor(s / 3600) + "h";
        return Math.floor(s / 86400) + "d";
    }
    function handoffText() {
        const h = menu.handoff;
        switch (h.state) {
        case "clean": return "clean · handed off " + ago(h.last_ok) + " ago";
        case "pushed": return "pushed " + ago(h.last_ok) + " ago";
        case "error": return "failed: " + (h.last_error ?? "");
        case "skipped": return "skipped: " + (h.last_skip ?? "");
        default: return "no handoff yet";
        }
    }
    function handoffColor() {
        return menu.handoff.state === "error" ? bad : menu.handoff.state === "skipped" ? warn : ink;
    }

    component Title: Text {
        Layout.fillWidth: true
        Layout.preferredHeight: menu.titleHeight
        verticalAlignment: Text.AlignBottom
        color: menu.dim
        font.family: "JetBrainsMono NFM"
        font.pixelSize: 10
        font.letterSpacing: 1.5
    }
    component Row2: RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: menu.rowHeight
        spacing: 8
    }
    component Cell: Text {
        color: menu.ink
        font.family: "JetBrainsMono NFM"
        font.pixelSize: 12
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
        Layout.preferredHeight: menu.rowHeight
    }

    ColumnLayout {
        id: layout
        width: menu.layoutWidth
        anchors.top: parent.top
        anchors.topMargin: 14
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 0

        Row2 {
            Cell { text: "THIS MACHINE"; color: menu.dim; font.pixelSize: 10; font.letterSpacing: 1.5; Layout.preferredWidth: 110 }
            Cell { text: menu.handoffText(); color: menu.handoffColor(); Layout.fillWidth: true }
        }

        Title { text: "SYNCTHING" }
        Row2 {
            Cell {
                Layout.fillWidth: true
                color: menu.syncthing.available === false ? menu.bad : menu.muted
                text: menu.syncthing.available === false ? "not running"
                    : menu.idleFolders + " idle" + (menu.syncthing.paused ? " · " + menu.syncthing.paused + " paused" : "")
            }
        }
        Repeater {
            model: menu.shownFolders
            Row2 {
                required property var modelData
                Cell { text: modelData.label; Layout.fillWidth: true }
                Cell {
                    text: modelData.errors ? modelData.errors + " errors" : modelData.need ? modelData.need + " pending" : modelData.state
                    color: modelData.errors ? menu.bad : menu.warn
                }
            }
        }

        Title { text: "INCOMING" + (menu.incoming.length ? "  " + menu.incoming.length : "") }
        Row2 {
            visible: menu.incoming.length === 0
            Cell { text: "nothing waiting"; color: menu.muted; Layout.fillWidth: true }
        }
        Repeater {
            model: menu.incoming.slice(0, menu.maxIncoming)
            Row2 {
                required property var modelData
                Cell { text: modelData.project + (modelData.worktree !== "main" ? " / " + modelData.worktree : ""); Layout.fillWidth: true }
                Cell { text: modelData.from; color: menu.muted; Layout.preferredWidth: 70 }
                Cell { text: menu.ago(modelData.when); color: menu.dim; Layout.preferredWidth: 32; horizontalAlignment: Text.AlignRight }
            }
        }
        Row2 {
            visible: menu.incoming.length > menu.maxIncoming
            Cell { text: "+" + (menu.incoming.length - menu.maxIncoming) + " more · projects incoming"; color: menu.dim; Layout.fillWidth: true }
        }
    }
}
