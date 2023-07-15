local gears = require('gears')
local awful = require('awful')
local hotkeys_popup = require('awful.hotkeys_popup')

require('awful.hotkeys_popup.keys')

local ctrl = "Control"
local shift = "Shift"

GlobalKeys = gears.table.join(
-- Launcher
-- Terminal
    awful.key({ Modkey }, "t", function() awful.spawn(Preferences.term) end,
        { description = "open terminal", group = "launcher" }),

    -- Browser
    awful.key({ Modkey }, "b", function() awful.spawn.with_shell(Preferences.web) end,
        { description = "open web browser", group = "launcher" }),

    -- Rofi -> Apps
    awful.key({ Modkey }, "Return", function() awful.spawn("rofi -show drun") end,
        { description = "open an app", group = "launcher" }),
    -- Rofi -> Emojis
    awful.key({ Modkey, shift }, "e", function() awful.spawn("rofi -show emoji") end,
        { description = "select an emoji", group = "launcher" }),
    -- Rofi -> Calculator
    awful.key({ Modkey }, "c", function() awful.spawn("rofi -show calc -no-show-match -no-sort") end,
        { description = "open calculator", group = "launcher" }),
    -- Rofi -> Bluetooth manager
    awful.key({ Modkey, shift }, "b", function() awful.spawn("rofi-bluetooth") end,
        { description = "open bluetooth settings", group = "settings" }),
    -- Rofi -> Network manager
    awful.key({ Modkey, shift }, "w", function() awful.spawn("rofi-net") end,
        { description = "open network settings", group = "settings" }),


    -- File manager
    awful.key({ Modkey }, "e", function() awful.spawn(Preferences.files) end,
        { description = "open file manager", group = "launcher" }),

    -- Awesome
    -- Help
    awful.key({ Modkey, }, "s", hotkeys_popup.show_help,
        { description = "show help", group = "awesome" }),
    -- Reload
    awful.key({ Modkey, ctrl }, "r", awesome.restart,
        { description = "reload awesome", group = "awesome" }),
    -- Quit
    awful.key({ Modkey, shift }, "q", awesome.quit,
        { description = "quit awesome", group = "awesome" }),

    -- Focus
    awful.key({ Modkey, }, "j", function() awful.client.focus.byidx(-1) end,
        { description = "focus next by index", group = "client" }),
    awful.key({ Modkey, }, "k", function() awful.client.focus.byidx(1) end,
        { description = "focus previous by index", group = "client" }),

    -- Screen Focus
    awful.key({ Modkey, ctrl }, "j", function() awful.screen.focus_relative(1) end,
        { description = "focus the next screen", group = "screen" }),
    awful.key({ Modkey, ctrl }, "k", function() awful.screen.focus_relative(-1) end,
        { description = "focus the previous screen", group = "screen" }),

    -- Restore Minimize
    awful.key({ Modkey, ctrl }, "n", function()
            local c = awful.client.restore()
            if c then
                c:emit_signal("request::activate", "key.unminimize", { raise = true })
            end
        end,
        { description = "restore minimized", group = "client" }),

    -- Go to previous
    awful.key({ Modkey, }, "Tab", function()
        awful.client.focus.history.previous()
        if client.focus then
            client.focus:raise()
        end
    end, { description = "go back", group = "client" }),

    -- Layout stuff
    awful.key({ Modkey, shift }, "d", function() awful.client.swap.byidx(1) end,
        { description = "swap with next client by index", group = "client" }),
    awful.key({ Modkey, shift }, "a", function() awful.client.swap.byidx(-1) end,
        { description = "swap with previous client by index", group = "client" }),
    awful.key({ Modkey, }, "u", awful.client.urgent.jumpto,
        { description = "jump to urgent client", group = "client" }),
    awful.key({ Modkey, }, "l", function() awful.tag.incmwfact(0.05) end,
        { description = "increase master width factor", group = "layout" }),
    awful.key({ Modkey, }, "h", function() awful.tag.incmwfact(-0.05) end,
        { description = "decrease master width factor", group = "layout" }),
    awful.key({ Modkey, shift }, "h", function() awful.tag.incnmaster(1, nil, true) end,
        { description = "increase the number of master clients", group = "layout" }),
    awful.key({ Modkey, shift }, "l", function() awful.tag.incnmaster(-1, nil, true) end,
        { description = "decrease the number of master clients", group = "layout" }),
    awful.key({ Modkey, ctrl }, "h", function() awful.tag.incncol(1, nil, true) end,
        { description = "increase the number of columns", group = "layout" }),
    awful.key({ Modkey, ctrl }, "l", function() awful.tag.incncol(-1, nil, true) end,
        { description = "decrease the number of columns", group = "layout" }),
    awful.key({ Modkey, }, "space", function() awful.layout.inc(1) end,
        { description = "select next", group = "layout" }),
    awful.key({ Modkey, shift }, "space", function() awful.layout.inc(-1) end,
        { description = "select previous", group = "layout" })
)

-- Tags
for i = 1, 3 do
    GlobalKeys = gears.table.join(GlobalKeys,

        -- View tag only.
        awful.key({ Modkey }, "#" .. i + 9,
            function()
                local screen = awful.screen.focused()
                local tag = screen.tags[i]
                if tag then
                    tag:view_only()
                end
            end,
            { description = "view tag", group = "tag" }),

        -- Toggle tag display.
        awful.key({ Modkey, ctrl }, "#" .. i + 9,
            function()
                local screen = awful.screen.focused()
                local tag = screen.tags[i]
                if tag then
                    awful.tag.viewtoggle(tag)
                end
            end,
            { description = "toggle tag", group = "tag" }),

        -- Move client to tag.
        awful.key({ Modkey, shift }, "#" .. i + 9,
            function()
                if client.focus then
                    local tag = client.focus.screen.tags[i]
                    if tag then
                        client.focus:move_to_tag(tag)
                    end
                end
            end,
            { description = "move focused client to tag", group = "tag" }),

        -- Toggle tag on focused client.
        awful.key({ Modkey, ctrl, shift }, "#" .. i + 9,
            function()
                if client.focus then
                    local tag = client.focus.screen.tags[i]
                    if tag then
                        client.focus:toggle_tag(tag)
                    end
                end
            end,
            { description = "toggle focused client on tag", group = "tag" })


    )
end


-- Client
ClientKeys = gears.table.join(
-- Fullscreen
    awful.key({ Modkey }, "f", function(c)
        c.fullscreen = not c.fullscreen
        c:raise()
    end, { description = "toggle fullscreen", group = "client" }),

    -- Close
    awful.key({ Modkey }, "q", function(c) c:kill() end,
        { description = "close", group = "client" }),

    -- Floating
    awful.key({ Modkey, }, "x", awful.client.floating.toggle,
        { description = "toggle floating", group = "client" }),

    -- Go to master
    awful.key({ Modkey, ctrl }, "Return", function(c)
            c:swap(awful.client.getmaster())
        end,
        { description = "move to master", group = "client" }),

    -- Move to other screen
    awful.key({ Modkey, }, "o", function(c) c:move_to_screen() end,
        { description = "move to screen", group = "client" }),

    -- Keep on top
    awful.key({ Modkey, }, "t", function(c) c.ontop = not c.ontop end,
        { description = "toggle keep on top", group = "client" }),

    -- (un)Maximize
    awful.key({ Modkey, }, "m",
        function(c)
            c.maximized = not c.maximized
            c:raise()
        end,
        { description = "(un)maximize", group = "client" }),

    -- Minimize
    awful.key({ Modkey, }, "n", function(c) c.minimized = true end,
        { description = "minimize", group = "client" })


)

-- Client Buttons
Clientbuttons = gears.table.join(
    awful.button({}, 1, function(c)
        c:emit_signal("request::activate", "mouse_click", { raise = true })
    end),
    awful.button({ Modkey }, 1, function(c)
        c:emit_signal("request::activate", "mouse_click", { raise = true })
        awful.mouse.client.move(c)
    end),
    awful.button({ Modkey }, 3, function(c)
        c:emit_signal("request::activate", "mouse_click", { raise = true })
        awful.mouse.client.resize(c)
    end)
)


root.keys(GlobalKeys)
return {
    clientkeys = ClientKeys,
    clientbuttons = Clientbuttons
}
