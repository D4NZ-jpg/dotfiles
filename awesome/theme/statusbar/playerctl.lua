local wibox = require('wibox')

M = wibox.widget {
    markup = 'Nothing Playing',
    align = "center",
    widget = wibox.widget.textbox
}

local playerctl = Bling.signal.playerctl.lib {
    ignore = "firefox",
    player = { "spotify", "%any" }
}

-- Hide/Show when music start/end
playerctl:connect_signal("playback_status",
    function(_, playing)
        M.visible = playing
    end)

-- Update metadata on change
playerctl:connect_signal("metadata",
    function(_, title, artist)
        M:set_markup_silently(title .. " - " .. artist)
    end)

return M
