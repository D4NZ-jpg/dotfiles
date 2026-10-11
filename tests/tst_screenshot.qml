import QtQuick
import QtTest
import "../dot_config/quickshell/panel" as Panel

TestCase {
    id: suite
    name: "ScreenshotKeyboard"
    width: 560; height: 320
    visible: true
    when: windowShown
    Panel.ScreenshotContent { id: menu; anchors.fill: parent }
    SignalSpy { id: captureSpy; target: menu; signalName: "captured" }
    SignalSpy { id: dismissSpy; target: menu; signalName: "dismissed" }
    function find(parent, predicate, out) {
        out = out || [];
        if (predicate(parent)) out.push(parent);
        for (const child of parent.children || []) find(child, predicate, out);
        return out;
    }
    function init() {
        menu.mode = "region";
        menu.destination = "clipboard";
        menu.menuOpen = false;
        captureSpy.clear(); dismissSpy.clear();
        menu.forceActiveFocus();
        waitForRendering(menu);
    }
    function test_enter_after_tab() {
        keyClick(Qt.Key_2);
        keyClick(Qt.Key_B);
        keyClick(Qt.Key_Tab);
        verify(!menu.activeFocus, "Tab moves focus to a child control");
        keyClick(Qt.Key_Return);
        tryCompare(captureSpy, "count", 1);
        compare(captureSpy.signalArguments[0][0], "window");
        compare(captureSpy.signalArguments[0][1], "both");
    }
    function test_escape_after_tab() {
        keyClick(Qt.Key_Tab);
        keyClick(Qt.Key_Escape);
        tryCompare(dismissSpy, "count", 1);
        compare(captureSpy.count, 0);
    }
    function test_keyboard_menu() {
        keyClick(Qt.Key_O);
        verify(menu.menuOpen);
        keyClick(Qt.Key_Down);
        keyClick(Qt.Key_Return);
        compare(menu.destination, "folder");
        verify(!menu.menuOpen);
        compare(captureSpy.count, 0);
        keyClick(Qt.Key_Return);
        tryCompare(captureSpy, "count", 1);
        compare(captureSpy.signalArguments[0][1], "folder");
    }
    function test_escape_closes_menu_before_toolbar() {
        keyClick(Qt.Key_O);
        keyClick(Qt.Key_Escape);
        verify(!menu.menuOpen);
        compare(dismissSpy.count, 0);
        keyClick(Qt.Key_Escape);
        compare(dismissSpy.count, 1);
    }
    function test_space_selects_focused_mode() {
        const screen = find(menu, b => b.glyph === "screen")[0];
        screen.forceActiveFocus();
        keyClick(Qt.Key_Space);
        compare(menu.mode, "screen");
        compare(captureSpy.count, 0);
    }
    function test_mouse_menu_selection() {
        const options = find(menu, b => b.chevron === true)[0];
        mouseClick(options);
        verify(menu.menuOpen);
        waitForRendering(menu);
        const both = find(menu, b => b.menuValue === "both")[0];
        mouseClick(both);
        compare(menu.destination, "both");
        verify(!menu.menuOpen);
        compare(captureSpy.count, 0);
    }
}
