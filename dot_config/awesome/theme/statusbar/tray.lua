local wibox      = require("wibox")
local awful      = require('awful')
local beautiful  = require("beautiful")
local gears      = require('gears')
local colors     = require('theme.colors')
local dpi        = beautiful.xresources.apply_dpi

local systray    = wibox.widget.systray()

local sys_widget = wibox.widget {
    text = "󰍝",
    font = beautiful.font .. dpi(20),
    widget = wibox.widget.textbox
}

local function get_current_screen()
    local mouse_coords = mouse.coords()

    for i = 1, screen:count() do
        local screen_geom = screen[i].geometry

        if mouse_coords.x >= screen_geom.x and

            mouse_coords.x < screen_geom.x + screen_geom.width and

            mouse_coords.y >= screen_geom.y and

            mouse_coords.y < screen_geom.y + screen_geom.height then
            return i
        end
    end

    return nil
end


local round_systray = wibox.widget {
    widget = wibox.container.constraint,
    height = dpi(37 * 3 + 10),
    forced_width = dpi(37 * 6 + 10),
    opacity = 1,
    {
        widget = wibox.container.background,
        bg = colors.bg_alt,
        {
            margins = dpi(5),
            widget = wibox.container.margin,
            systray
        }
    }
}

local pop_tray = awful.popup {
    widget       = round_systray,
    shape        = gears.shape.rounded_rect,
    visible      = false,
    ontop        = true,
    opacity      = 0.8,
    border_width = dpi(3),
    border_color = colors.accent_blue
}

pop_tray:connect_signal("mouse::leave", function()
    pop_tray.visible = false
    sys_widget.text = "󰍝"
end)

sys_widget.buttons = {
    awful.button({}, 1, function()
        local current_screen_index = get_current_screen()

        if current_screen_index ~= nil then
            systray.screen = screen[current_screen_index]
        end

        pop_tray.visible = not pop_tray.visible
        if pop_tray.visible then
            pop_tray:move_next_to(mouse.current_widget_geometry)
            systray.base_size = dpi(37)
            sys_widget.text = "󰍠"
        else
            sys_widget.text = "󰍝"
        end
    end), }

return sys_widget
