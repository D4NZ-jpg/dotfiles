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
    property var calls: []
    property var pendingDone: null
    function fakeRunner(args, done) { suite.calls.push(args.join(" ")); suite.pendingDone = done; }
    Panel.SyncContent { id: menu; status: suite.attention; width: 400; height: 700; runner: suite.fakeRunner; onDismissed: suite.dismissed++; onRefresh: suite.refreshed++ }
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
                // actions
                menu.status = suite.attention;
                const buttons = suite.findAll(menu, o => o.hasOwnProperty("text") && o.hasOwnProperty("down"));
                const handoffBtn = buttons.find(b => b.objectName === "handoffButton");
                const resumeBtn = buttons.find(b => b.objectName === "resumeAllButton");
                suite.check(handoffBtn.enabled && resumeBtn.enabled, "Both actions enabled when idle with incoming work");
                handoffBtn.clicked();
                suite.check(suite.calls.join("|") === "handoff", "Hand off runs `projects handoff`");
                suite.check(menu.running === "handoff" && !handoffBtn.enabled && !resumeBtn.enabled, "Actions disabled while running");
                suite.check(handoffBtn.text === "Handing off…", "Button shows progress");
                suite.pendingDone(true, "  ✓ rummy: 1 worktree(s) on server\n\n1 worktree snapshot(s) pushed in 1s\n");
                suite.check(menu.running === "" && menu.message === "1 worktree snapshot(s) pushed in 1s" && !menu.messageIsError, "Success summary is the last line");
                suite.check(suite.refreshed === 2, "Completion asks for a refresh");
                resumeBtn.clicked();
                suite.check(suite.calls[1] === "resume", "Resume all runs `projects resume` without --force");
                suite.pendingDone(true, "  ✗ Camtom: main: has local changes; run with --force to snapshot them\n  ✓ kernel: main ← macbook\n\n1 worktree(s) resumed; skipped: Camtom/main\n");
                suite.check(menu.messageIsError && menu.message.indexOf("kept local edits: Camtom") === 0, "Blocked worktrees are reported, not forced");
                const links = suite.findAll(menu, o => o.objectName === "resumeLink");
                suite.check(links.length === 3, "One resume link per incoming row");
                links[1].clicked();
                suite.check(suite.calls[2] === "resume nivra-app", "Row link resumes just that project");
                suite.check(links[1].text === "…", "Row shows progress while running");
                suite.pendingDone(false, "error: something broke");
                suite.check(menu.messageIsError && menu.message === "error: something broke", "Failure shows the last output line");
                menu.status = suite.quiet;
                suite.check(!resumeBtn.enabled, "Resume all disabled with nothing incoming");
                menu.runner = null;
                suite.check(!handoffBtn.enabled, "No runner means no actions");
                console.log("SYNC_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("SYNC_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
