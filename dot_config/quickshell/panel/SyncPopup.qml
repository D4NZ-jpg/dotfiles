import QtQuick
import Quickshell
import Quickshell.Io

PanelPopup {
    id: popup
    property var status: ({})
    signal refresh()
    layerNamespace: "dan-sync"
    contentHeight: content.implicitHeight

    // One `projects` invocation at a time; output collected for the summary line.
    Process {
        id: proc
        property var done: null
        property string buffer: ""
        stdout: StdioCollector { onStreamFinished: proc.buffer += text }
        stderr: StdioCollector { onStreamFinished: proc.buffer += text }
        onExited: (code, status) => {
            const cb = done, out = buffer;
            done = null;
            buffer = "";
            if (cb) cb(code === 0, out);
        }
    }
    function runProjects(args, done) {
        if (proc.running) return;
        proc.buffer = "";
        proc.done = done;
        proc.command = [Quickshell.env("HOME") + "/.local/bin/projects"].concat(args);
        proc.running = true;
    }

    SyncContent {
        id: content
        anchors.fill: parent
        status: popup.status
        runner: popup.runProjects
        onDismissed: popup.close()
        onRefresh: popup.refresh()
    }
}
