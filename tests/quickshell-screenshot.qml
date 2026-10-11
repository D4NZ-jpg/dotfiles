import QtQuick
import Quickshell
import "panel" as Panel

ShellRoot {
    id: suite
    property int checks: 0
    property int captures: 0
    property int dismissals: 0
    property string lastMode: ""
    property string lastDestination: ""
    function check(value, description) {
        if (!value) throw new Error(description);
        checks++;
    }
    function find(parent, predicate, out) {
        out = out || [];
        if (predicate(parent)) out.push(parent);
        for (const child of parent.children || []) find(child, predicate, out);
        return out;
    }
    Panel.ScreenshotContent {
        id: menu
        width: implicitWidth; height: implicitHeight
        onCaptured: (mode, destination) => { suite.captures++; suite.lastMode = mode; suite.lastDestination = destination; }
        onDismissed: suite.dismissals++
    }
    Timer {
        interval: 150; running: true
        onTriggered: {
            try {
                const modeButtons = suite.find(menu, o => o.hasOwnProperty("glyph") && ["screen", "window", "region"].includes(o.glyph));
                const options = suite.find(menu, o => o.hasOwnProperty("menuValue"));
                suite.check(menu.mode === "region" && menu.destination === "clipboard", "Safe initial selection");
                suite.check(suite.captures === 0 && !menu.menuOpen, "Opening does not capture or open the menu");
                suite.check(modeButtons.length === 3 && modeButtons.filter(b => b.selected).length === 1, "Three modes, one selected");
                suite.check(options.length === 3 && options.filter(o => o.current).length === 1, "Three destinations, one current");
                suite.check(menu.bar.height === 52 && menu.bar.width < 480, "Single compact row");
                for (const [key, mode] of [[Qt.Key_1, "screen"], [Qt.Key_2, "window"], [Qt.Key_3, "region"]])
                    suite.check(menu.handleKey(key) && menu.mode === mode, "Mode hotkey " + mode);
                suite.check(menu.handleKey(Qt.Key_Right) && menu.mode === "screen", "Right arrow wraps modes");
                suite.check(menu.handleKey(Qt.Key_Left) && menu.mode === "region", "Left arrow steps modes");
                for (const [key, destination] of [[Qt.Key_F, "folder"], [Qt.Key_B, "both"], [Qt.Key_C, "clipboard"]])
                    suite.check(menu.handleKey(key) && menu.destination === destination, "Destination hotkey " + destination);
                suite.check(menu.handleKey(Qt.Key_O) && menu.menuOpen && menu.menu.visible, "O opens Options");
                suite.check(menu.handleKey(Qt.Key_Escape) && !menu.menuOpen && suite.dismissals === 0, "Escape closes the menu first");
                const optionsButton = suite.find(menu, o => o.hasOwnProperty("chevron") && o.chevron)[0];
                optionsButton.clicked();
                suite.check(menu.menuOpen, "Options click opens the menu");
                options.find(o => o.menuValue === "folder").clicked();
                suite.check(menu.destination === "folder" && !menu.menuOpen, "Choosing a destination closes the menu");
                modeButtons.find(b => b.glyph === "window").clicked();
                suite.check(menu.mode === "window" && suite.captures === 0, "Mode click selects without capturing");
                suite.check(menu.handleKey(Qt.Key_Return) && suite.captures === 1, "Return captures once");
                suite.check(suite.lastMode === "window" && suite.lastDestination === "folder", "Capture routes selected values");
                suite.check(menu.handleKey(Qt.Key_Escape) && suite.dismissals === 1 && suite.captures === 1, "Escape dismisses without capture");
                suite.check(!menu.handleKey(Qt.Key_Tab), "Tab is delegated to focus traversal");
                suite.check(modeButtons.every(b => b.implicitWidth >= 44 && b.implicitHeight >= 36), "Adequate hit targets");
                console.log("SCREENSHOT_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("SCREENSHOT_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
