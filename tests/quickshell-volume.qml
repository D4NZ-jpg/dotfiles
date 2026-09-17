import QtQuick
import Quickshell
import Quickshell.Services.Pipewire
import "panel" as Panel

// Run through quickshell-panel.py. Fake nodes stand in for Pipewire; the
// real service is never touched.
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
    component FakeAudio: QtObject { property bool muted: false; property real volume: 0.5 }
    component FakeNode: QtObject {
        property string name: ""
        property string description: ""
        property string nickname: ""
        property bool isSink: false
        property bool isStream: false
        property bool ready: true
        property int type: PwNodeType.Audio
        property var properties: ({})
        property var audio: FakeAudio {}
    }
    FakeNode { id: speakers; name: "alsa_output.a"; description: "Speakers"; isSink: true }
    FakeNode { id: headset; name: "bluez_output.b"; description: "Headset"; isSink: true }
    FakeNode { id: mic; name: "alsa_input.c"; description: "Microphone" }
    FakeNode { id: unready; name: "alsa_input.d"; description: "Not ready"; ready: false }
    FakeNode { id: video; name: "v4l2.e"; description: "Camera"; type: PwNodeType.Video; audio: null }
    FakeNode { id: stream; name: "stream.f"; isStream: true; properties: ({"application.name": "Player", "media.name": "Song"}) }
    QtObject {
        id: service
        property bool ready: true
        property var nodes: ({values: [speakers, headset, mic, unready, video, stream]})
        property var defaultAudioSink: speakers
        property var defaultAudioSource: mic
        property var preferredDefaultAudioSink: null
        property var preferredDefaultAudioSource: null
    }
    Panel.VolumeContent { id: menu; service: service; width: 380; height: 560 }
    Timer {
        interval: 150
        running: true
        onTriggered: {
            try {
                suite.check(menu.sinks.length === 2 && menu.sources.length === 1 && menu.streams.length === 1, "Nodes sorted into sinks, sources and streams");
                suite.check(menu.audioNodes.indexOf(video) === -1, "Video nodes ignored");
                suite.check(menu.label(stream) === "Player · Song", "Stream label uses application and media name");
                suite.check(menu.label(speakers) === "Speakers", "Device label uses description");
                const sliders = suite.findAll(menu, o => o.objectName === "volumeSlider");
                suite.check(sliders.length === 4, "One slider per listed node, got " + sliders.length);
                const speakerSlider = sliders.find(s => s.Accessible.name === "Speakers volume");
                suite.check(speakerSlider !== undefined, "Speaker slider found");
                speakerSlider.value = 0.8;
                speakerSlider.moved();
                suite.check(Math.abs(speakers.audio.volume - 0.8) < 0.001, "Slider movement writes node volume");
                headset.audio.volume = 0.3;
                const headsetSlider = sliders.find(s => s.Accessible.name === "Headset volume");
                suite.check(Math.abs(headsetSlider.value - 0.3) < 0.001, "External volume change updates slider");
                const rows = suite.findAll(menu, o => o.hasOwnProperty("selectable") && o.hasOwnProperty("choose"));
                const headsetRow = rows.find(r => r.node === headset);
                suite.check(headsetRow.selectable && !headsetRow.selected, "Second sink is selectable and not default");
                headsetRow.choose();
                suite.check(service.preferredDefaultAudioSink === headset, "Choosing a sink sets the preferred default");
                const micRow = rows.find(r => r.node === mic);
                suite.check(!micRow.selectable, "Single source is not selectable");
                suite.check(service.preferredDefaultAudioSource === null, "Source default untouched");
                suite.check(!mic.audio.muted && !speakers.audio.muted && !stream.audio.muted, "Opening never mutes anything");
                console.log("VOLUME_TESTS_PASS " + suite.checks);
            } catch (error) {
                console.error("VOLUME_TESTS_FAIL " + error.message);
            }
            Qt.quit();
        }
    }
}
