import QtQuick
import QtQuick.Layouts

// Handoff and Syncthing state at a glance, with the two safe actions:
// hand off this machine's work, and resume incoming work (never --force;
// worktrees with local edits are reported instead of overwritten).
// `status` is the object written by sync-status.py; `runner` executes a
// `projects` argv and calls back, so tests can substitute a fake.
Item {
    id: menu
    property var status: ({})
    // runner(args: string[], done: function(ok: bool, output: string))
    property var runner: null
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
    readonly property var shownFolders: folders.filter(f => f.state !== "idle" && f.state !== "paused")
    readonly property int idleFolders: folders.filter(f => f.state === "idle").length
    readonly property int maxIncoming: 8

    property string running: ""       // "" | "handoff" | "resume" | "resume:<project>"
    property string message: ""
    property bool messageIsError: false

    implicitWidth: 400
    readonly property int rowHeight: 24
    readonly property int titleHeight: 26
    readonly property int actionHeight: 34
    implicitHeight: {
        let h = 14 + rowHeight;                                   // handoff line
        h += actionHeight;                                        // action row
        h += 18;                                                  // message line
        h += titleHeight + rowHeight * (shownFolders.length + 1); // syncthing block
        h += titleHeight + rowHeight * Math.max(1, Math.min(incoming.length, maxIncoming));
        if (incoming.length > maxIncoming) h += rowHeight;
        return h + 14;
    }
    readonly property int layoutWidth: width > 0 ? width : implicitWidth

    focus: true
    Keys.onEscapePressed: dismissed()
    Keys.onPressed: event => {
        if (event.key === Qt.Key_R) { refresh(); event.accepted = true; }
        else if (event.key === Qt.Key_H) { handOff(); event.accepted = true; }
        else if (event.key === Qt.Key_A) { resumeAll(); event.accepted = true; }
    }

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

    // Reduce `projects` output to one line for the message slot.
    function summarize(args, ok, output) {
        const lines = output.split("\n").map(l => l.trim()).filter(l => l !== "");
        const last = lines.length ? lines[lines.length - 1] : "";
        const blocked = lines.filter(l => l.indexOf("has local changes") !== -1)
            .map(l => l.replace(/^[✗✓!·\s]*/, "").split(":")[0]);
        if (blocked.length) return { text: "kept local edits: " + blocked.join(", ") + " (resume --force in a terminal to take the Mac's)", error: true };
        if (!ok) return { text: last || "failed", error: true };
        return { text: last.replace(/^[✓\s]*/, ""), error: false };
    }
    function run(kind, args) {
        if (!runner || running !== "") return;
        running = kind;
        message = "";
        messageIsError = false;
        runner(args, (ok, output) => {
            const r = summarize(args, ok, output);
            message = r.text;
            messageIsError = r.error;
            running = "";
            refresh();
        });
    }
    function handOff() { run("handoff", ["handoff"]); }
    function resumeAll() { run("resume", ["resume"]); }
    function resumeOne(project) { run("resume:" + project, ["resume", project]); }

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
    component Link: Text {
        // small inline action, used per incoming row
        property bool active: true
        signal clicked()
        color: active ? menu.warn : menu.dim
        font.family: "JetBrainsMono NFM"
        font.pixelSize: 11
        verticalAlignment: Text.AlignVCenter
        Layout.preferredHeight: menu.rowHeight
        MouseArea { anchors.fill: parent; cursorShape: parent.active ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: if (parent.active) parent.clicked() }
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
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: menu.actionHeight
            spacing: 8
            PanelAction {
                objectName: "handoffButton"
                text: menu.running === "handoff" ? "Handing off…" : "Hand off"
                enabled: menu.running === "" && !!menu.runner
                onClicked: menu.handOff()
            }
            PanelAction {
                objectName: "resumeAllButton"
                text: menu.running === "resume" ? "Resuming…" : "Resume all"
                enabled: menu.running === "" && !!menu.runner && menu.incoming.length > 0
                onClicked: menu.resumeAll()
            }
            Item { Layout.fillWidth: true }
            Cell { text: "h · a · r"; color: menu.dim; font.pixelSize: 10 }
        }
        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: 18
            text: menu.message
            textFormat: Text.PlainText
            color: menu.messageIsError ? menu.bad : menu.muted
            font.family: "JetBrainsMono NFM"
            font.pixelSize: 11
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
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
                Cell { text: modelData.from; color: menu.muted; Layout.preferredWidth: 64 }
                Cell { text: menu.ago(modelData.when); color: menu.dim; Layout.preferredWidth: 28; horizontalAlignment: Text.AlignRight }
                Link {
                    objectName: "resumeLink"
                    text: menu.running === "resume:" + modelData.project ? "…" : "resume"
                    active: menu.running === "" && !!menu.runner
                    onClicked: menu.resumeOne(modelData.project)
                }
            }
        }
        Row2 {
            visible: menu.incoming.length > menu.maxIncoming
            Cell { text: "+" + (menu.incoming.length - menu.maxIncoming) + " more · projects incoming"; color: menu.dim; Layout.fillWidth: true }
        }
    }
}
