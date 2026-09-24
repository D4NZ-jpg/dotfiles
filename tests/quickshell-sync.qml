import QtQuick
import Quickshell
import "panel" as Panel

// Run through quickshell-panel.py. A synthetic status object stands in for
// the JSON written by sync-status.py.
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
    function texts(item) {
        return suite.findAll(item, o => o.hasOwnProperty("text") && o.hasOwnProperty("elide")).map(o => o.text);
    }
    readonly property int now: Math.floor(Date.now() / 1000)
    property var attention: ({
        level: "attention",
        handoff: { state: "clean", last_ok: now - 300 },
        incoming: [
            { project: "Camtom", worktree: "main", from: "macbook", when: now - 3600 },
            { project: "nivra-app", worktree: "main", from: "macbook", when: now - 7200 },
            { project: "Camtom", worktree: "Camtom-mve-schema", from: "macbook", when: now - 90000 }
        ],
        syncthing: { available: true, syncing: 1, errors: 0, paused: 2, folders: [
            { label: "ai", state: "idle", need: 0, errors: 0 },
            { label: "nivra", state: "syncing", need: 12, errors: 0 },
            { label: "Music", state: "paused", need: 0, errors: 0 },
            { label: "Books", state: "paused", need: 0, errors: 0 }
        ] }
    })
    property var quiet: ({
        level: "idle",
        handoff: { state: "clean", last_ok: now - 60 },
        incoming: [],
        syncthing: { available: true, syncing: 0, errors: 0, paused: 0, folders: [ { label: "ai", state: "idle", need: 0, errors: 0 } ] }
    })
    property var broken: ({
        level: "error",
        handoff: { state: "error", last_error: "Camtom failed" },
        incoming: [],
        syncthing: { available: true, syncing: 0, errors: 1, paused: 0, folders: [ { label: "final", state: "error", need: 0, errors: 3 } ] }
    })
    property int dismissed: 0
    property int refreshed: 0
    Panel.SyncContent { id: menu; status: suite.attention; width: 380; height: 600; onDismissed: suite.dismissed++; onRefresh: suite.refreshed++ }
    Timer {
        interval: 100
        running: true
        onTriggered: {
            try {
                let t = suite.texts(menu);
                suite.check(t.some(x => x.indexOf("clean · handed off 5m ago") === 0), "Handoff line shows clean + age");
                suite.check(t.indexOf("1 idle · 2 paused") !== -1, "Idle and paused folders summarised");
                suite.check(menu.shownFolders.length === 1 && menu.shownFolders[0].label === "nivra", "Only active folders listed");
                suite.check(t.indexOf("12 pending") !== -1, "Pending count shown for syncing folder");
                suite.check(t.indexOf("INCOMING  3") !== -1, "Incoming title carries the count");
                suite.check(t.indexOf("Camtom") !== -1 && t.indexOf("Camtom / Camtom-mve-schema") !== -1, "Main worktree bare, others suffixed");
                suite.check(t.indexOf("1h") !== -1 && t.indexOf("1d") !== -1, "Ages rendered compactly");
                const h1 = menu.implicitHeight;
                menu.status = suite.quiet;
                t = suite.texts(menu);
                suite.check(t.indexOf("nothing waiting") !== -1, "Empty incoming has a placeholder");
                suite.check(menu.implicitHeight < h1, "Height shrinks with fewer rows");
                menu.status = suite.broken;
                t = suite.texts(menu);
                suite.check(t.some(x => x === "failed: Camtom failed"), "Handoff error text");
                suite.check(t.indexOf("3 errors") !== -1, "Folder error count");
                suite.check(menu.handoffColor() === menu.bad, "Error uses the red tone");
                menu.status = { level: "idle", incoming: [], syncthing: { available: false, folders: [] } };
                suite.check(suite.texts(menu).indexOf("not running") !== -1, "Syncthing unavailable is stated");
                suite.check(menu.implicitHeight > 0, "Height computed with empty status");
                menu.dismissed();
                suite.check(suite.dismissed === 1, "dismissed signal reaches the popup");
                menu.refresh();
                suite.check(suite.refreshed === 1, "refresh signal reaches the popup");
                console.log("SYNC_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("SYNC_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
