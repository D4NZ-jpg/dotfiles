local awful     = require("awful")
local wibox     = require("wibox")
local gears     = require("gears")
local colors    = require("theme.colors")
local beautiful = require("beautiful")
local dpi       = beautiful.xresources.apply_dpi

require('theme.wallpaper')

local taglistbuttons = require('theme.statusbar.taglist')
local tasklistbuttons = require('theme.statusbar.tasklist')
local clock = wibox.widget.textclock()
local playerctl = require('theme.statusbar.playerctl')
local sys_widget = require('theme.statusbar.tray')
local extra = require('theme.statusbar.misc')

awful.screen.connect_for_each_screen(function(s)
    -- Wallpaper
    Set_wallpaper(s)

    -- Each screen has its own tag table.
    awful.tag({ "1", "2", "3" }, s, awful.layout.suit.tile.left)

    -- Create an imagebox widget which will contain an icon indicating which layout we're using
    -- We need one layoutbox per screen.
    s.layout_box = awful.widget.layoutbox(s)
    s.layout_box:buttons(gears.table.join(
        awful.button({}, 1, function() awful.layout.inc(1) end),
        awful.button({}, 3, function() awful.layout.inc(-1) end),
        awful.button({}, 4, function() awful.layout.inc(1) end),
        awful.button({}, 5, function() awful.layout.inc(-1) end)))

    -- taglist widget
    s.taglist = awful.widget.taglist {
        screen          = s,
        filter          = awful.widget.taglist.filter.all,
        buttons         = taglistbuttons,

        widget_template = {
            {
                margins = dpi(5),
                widget = wibox.container.margin
            },
            shape = gears.shape.circle,
            bg = colors.black,
            widget = wibox.container.background,
            create_callback = function(self, t)
                if t.selected then
                    self.bg = colors.accent_1
                else
                    self.bg = colors.black
                end
            end,

            update_callback = function(self, t)
                if t.selected then
                    self.bg = colors.accent_1
                else
                    self.bg = colors.black
                end
            end
        }
    }

    s.tasklist = awful.widget.tasklist {
        screen = s,
        filter = awful.widget.tasklist.filter.currenttags,
        bttons = tasklistbuttons,

        widget_template = {
            widget = wibox.container.background,
            {
                valign = "center",
                halign = "center",
                widget = wibox.container.place,
                {
                    margins = dpi(2),
                    widget = wibox.container.margin,
                    {
                        id = "clienticon",
                        widget = awful.widget.clienticon,
                        valign = "center"
                    }
                },
            },
            create_callback = function(self, c)
                -- Show active window
                if c.active then
                    self.bg = colors.black
                else
                    self.bg = colors.transparent
                end
                -- Make minimized window transparent
                local prev = self.opacity
                if c.minimized then
                    self.opacity = 0.2
                else
                    self.opacity = 1
                end


                self:get_children_by_id("clienticon")[1].client = c
            end,

            update_callback = function(self, c)
                -- Show active window
                if c.active then
                    self.bg = colors.black
                else
                    self.bg = colors.transparent
                end

                -- Make minimized window transparent
                local prev = self.opacity
                if c.minimized then
                    self.opacity = 0.2
                else
                    self.opacity = 1
                end

                if prev ~= self.opacity then
                    self:emit_signal("widget::redraw_needed")
                end
            end

        }
    }

    s.statusbar = awful.wibar({
        position = "top",
        screen = s,
        opacity = 0.8,
        bg = colors.bg,
        fg = colors.accent_1,
    })

    -- Add widgets to the wibox
    s.statusbar:setup {
        layout = wibox.layout.align.horizontal,
        expand = "none",
        { -- Left widgets
            layout = wibox.layout.fixed.horizontal,
            {
                text = " 󰣇 ",
                font = beautiful.font .. dpi(20),
                widget = wibox.widget.textbox
            },
            s.taglist,
            {
                margins = dpi(5),
                widget = wibox.container.margin
            },
            s.tasklist,

        },
        { -- Center widget
            playerctl,
            left = dpi(10),
            right = dpi(10),
            widget = wibox.container.margin
        },
        { -- Right widgets
            layout = wibox.layout.fixed.horizontal,
            {
                widget = wibox.container.margin,
                right = dpi(25),
                {
                    layout = wibox.layout.fixed.horizontal,
                    {
                        widget = wibox.container.margin,
                        right = dpi(5),
                        {
                            text = "",
                            font = beautiful.font .. dpi(17),
                            widget = wibox.widget.textbox,
                        }
                    },
                    {
                        widget = wibox.container.place,
                        extra.cpu,
                    }
                }
            },
            {
                layout = wibox.layout.fixed.horizontal,
                {
                    text = "󰥔",
                    font = beautiful.font .. dpi(16),
                    widget = wibox.widget.textbox
                },
                clock,
            },
            awful.widget.keyboardlayout,
            s.layout_box,
            sys_widget,
            {
                margins = dpi(3),
                widget = wibox.container.margin
            }
        }
    }
end)
