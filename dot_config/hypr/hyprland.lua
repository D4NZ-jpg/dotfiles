-- Hyprland 0.56.2+ with pinned upstream hyprsplit workspace management.
local root = debug.getinfo(1, "S").source:sub(2):match("^(.*)/")
local hs = dofile(root .. "/vendor/hyprsplit/init.lua")
hs.config({ num_workspaces = 20, persistent_workspaces = false })
hs.monitor_priority({ "DP-1", "HDMI-A-2" })
local rows = dofile(root .. "/modules/workspace-bindings.lua").new(hl, hs)
local pads = dofile(root .. "/modules/scratchpads.lua").new(hl)
-- Exposed for Lua IPC actions; no shell helper moves windows.
workspace_rows = rows
-- Reuse the same scratchpad controller for panel clicks and keybinds.
function panel_scratchpad(name, monitor)
    assert(name == "volume" or name == "bluetooth", "Unknown panel scratchpad")
    hl.plugin.scrolloverview._dispatch("overview", "off all")
    hl.dispatch(hl.dsp.focus({ monitor = monitor }))
    pads.toggle(name)
end

hl.monitor({ output = "DP-1", mode = "1440x900", position = "0x0", scale = 1 })
-- Use the actual connector; the legacy config still referred to HDMI-A-1.
hl.monitor({ output = "HDMI-A-2", mode = "1920x1080", position = "1440x0", scale = 1 })
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
hl.env("XCURSOR_SIZE", "16")
hl.env("XCURSOR_THEME", "GoogleDot-White")
hl.config({
    cursor = { default_monitor = "HDMI-A-2", inactive_timeout = 10, hide_on_key_press = true, hide_on_touch = true },
    input = { kb_layout = "us,latam", kb_options = "grp:alt_shift_toggle", follow_mouse = 1,
        sensitivity = 0, touchpad = { natural_scroll = false } },
    general = { layout = "scrolling", gaps_in = 5, gaps_out = 10, border_size = 3,
        col = { active_border = "rgb(afa286)", inactive_border = "rgb(49453d)" } },
    decoration = { rounding = 10, active_opacity = 1, inactive_opacity = 0.9, fullscreen_opacity = 1,
        blur = { enabled = true, size = 4, passes = 3, new_optimizations = true } },
    animations = { enabled = true, workspace_wraparound = false },
    scrolling = { direction = "right", column_width = 1.0, fullscreen_on_one_column = false,
        focus_fit_method = 1, follow_focus = true, explicit_column_widths = "0.333, 0.5, 0.667, 1.0",
        wrap_focus = false, wrap_swapcol = false },
    plugin = { scrolloverview = { layout = "vertical", scale = 0.5, blur = false } },
    misc = { disable_hyprland_logo = true },
})
hl.curve("myBezier", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.05 } } })
for _, anim in ipairs({
    { "windows", 5, "myBezier" }, { "windowsOut", 5, "default", "popin 80%" },
    { "border", 7, "default" }, { "borderangle", 8, "default" },
    { "fade", 5, "default" }, { "workspaces", 2.5, "default", "slidevert" },
    { "layersIn", 2, "default" }, { "fadeLayersIn", 2, "default" },
}) do
    hl.animation({ leaf = anim[1], enabled = true, speed = anim[2], bezier = anim[3], style = anim[4] })
end
local function bind(key, callback, opts) hl.bind("SUPER + " .. key, callback, opts) end
local function exec(command) return hl.dsp.exec_cmd(command) end
bind("T", exec("kitty"))
bind("B", exec("zen-browser"))
bind("Q", hl.dsp.window.close())
bind("SHIFT + Q", hl.dsp.exit())
bind("X", hl.dsp.window.float({ action = "toggle" }))
bind("F", hl.dsp.layout("colresize 1.0"))
bind("SHIFT + F", hl.dsp.window.fullscreen())
bind("R", hl.dsp.layout("colresize +conf"))
bind("SHIFT + R", hl.dsp.layout("colresize -conf"))
-- ScrollOverview is installed by setup/scripts/hyprland-plugins.sh.
bind("O", function() hl.plugin.scrolloverview._dispatch("overview", "toggle all") end)
-- ScrollOverview owns this mode's lifecycle, including mouse/Escape exits.
-- Quickshell observes the compositor's submap events, not a parallel toggle.
hl.define_submap("scrolloverview", function()
    for _, direction in ipairs({ "left", "right", "up", "down" }) do
        hl.bind(direction, function() hl.plugin.scrolloverview._dispatch("navigate", direction) end)
    end
    for key, direction in pairs({ H = "left", J = "down", K = "up", L = "right" }) do
        hl.bind("SUPER + " .. key, function() hl.plugin.scrolloverview._dispatch("navigate", direction) end)
    end
    -- Focus the overview selection before moving it; keep the overview open.
    local function moveOverview(action)
        hl.plugin.scrolloverview._dispatch("overview", "select")
        hl.plugin.scrolloverview._dispatch("window", "select")
        action()
    end
    hl.bind("SUPER + SHIFT + H", function()
        moveOverview(function() hl.dispatch(hl.dsp.layout("swapcol l")) end)
    end)
    hl.bind("SUPER + SHIFT + L", function()
        moveOverview(function() hl.dispatch(hl.dsp.layout("swapcol r")) end)
    end)
    hl.bind("SUPER + SHIFT + J", function()
        moveOverview(function() rows.step(1, true) end)
    end)
    hl.bind("SUPER + SHIFT + K", function()
        moveOverview(function() rows.step(-1, true) end)
    end)
    hl.bind("SUPER + CTRL + SHIFT + H", function()
        moveOverview(function() hl.dispatch(hl.dsp.window.move({ monitor = "l", follow = true })) end)
    end)
    hl.bind("SUPER + CTRL + SHIFT + L", function()
        moveOverview(function() hl.dispatch(hl.dsp.window.move({ monitor = "r", follow = true })) end)
    end)
    hl.bind("SUPER + Q", function()
        hl.plugin.scrolloverview._dispatch("window", "close")
    end)
    local function selectOverview()
        hl.plugin.scrolloverview._dispatch("overview", "select")
        hl.plugin.scrolloverview._dispatch("window", "select")
        hl.plugin.scrolloverview._dispatch("overview", "off all")
    end
    hl.bind("RETURN", selectOverview)
    hl.bind("ESCAPE", function() hl.plugin.scrolloverview._dispatch("overview", "off all") end)
    hl.bind("SUPER + O", function() hl.plugin.scrolloverview._dispatch("overview", "off all") end)
    hl.bind("mouse:272", selectOverview, { mouse = true })
end)
bind("SHIFT + P", exec("wlogout"))
bind("CTRL + H", hl.dsp.focus({ monitor = "l" }))
bind("CTRL + L", hl.dsp.focus({ monitor = "r" }))
bind("CTRL + SHIFT + H", hl.dsp.window.move({ monitor = "l", follow = true }))
bind("CTRL + SHIFT + L", hl.dsp.window.move({ monitor = "r", follow = true }))
bind("SPACE", exec("rofi -show drun"))
bind("E", exec("rofi -show emoji"))
bind("C", exec("rofi -show calc -no-show-match -no-sort"))
-- Layout focus keeps H/L on this monitor; monitor focus is explicitly Ctrl H/L.
bind("H", hl.dsp.layout("focus l"))
bind("L", hl.dsp.layout("focus r"))
bind("SHIFT + H", hl.dsp.layout("swapcol l"))
bind("SHIFT + L", hl.dsp.layout("swapcol r"))
bind("J", function() rows.step(1, false) end)
bind("K", function() rows.step(-1, false) end)
bind("SHIFT + J", function() rows.step(1, true) end)
bind("SHIFT + K", function() rows.step(-1, true) end)
bind("mouse_down", function() rows.step(1, false) end)
bind("mouse_up", function() rows.step(-1, false) end)
bind("ALT + P", exec('"$HOME/.config/scripts/rofi-screenshot-wayland.sh"'))
bind("mouse:272", hl.dsp.window.drag(), { mouse = true })
bind("mouse:273", hl.dsp.window.resize(), { mouse = true })
bind("A", function() pads.toggle("term") end)
bind("CTRL + V", function() pads.toggle("volume") end)
bind("CTRL + B", function() pads.toggle("bluetooth") end)
hl.bind("XF86MonBrightnessDown", exec("brightnessctl set 10%-"))
hl.bind("XF86MonBrightnessUp", exec("brightnessctl set +10%"))
-- Preserve the existing notes shortcut without relying on a legacy submap file.
bind("N", hl.dsp.submap("notes"))
hl.define_submap("notes", function()
hl.bind("I", function()
    hl.dispatch(hl.dsp.exec_cmd('"$HOME/notes/99. Meta/rofi/scripts/idea.sh"'))
    hl.dispatch(hl.dsp.submap("reset"))
end)
hl.bind("catchall", hl.dsp.submap("reset"))
end)

hl.on("hyprland.start", function()
    if hl.get_monitor("HDMI-A-2") then
        hl.dispatch(hl.dsp.focus({ monitor = "HDMI-A-2" }))
    end
    hl.exec_cmd('swaybg -i "$HOME/wallpapers/blackhole.png" -m fill')
    hl.exec_cmd("udiskie")
    hl.exec_cmd("quickshell -c panel -d --no-duplicate")
    hl.exec_cmd('hypridle -c "' .. root .. '/hypridle-lua.conf"')
    hl.exec_cmd("hyprpm reload -n")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'GoogleDot-White'")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 16")
    hl.exec_cmd("xdg-settings set default-web-browser zen.desktop")
end)
