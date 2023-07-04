local awful = require('awful')

local M = {}

local total_prev = 0
local idle_prev = 0

M.cpu = awful.widget.watch(
    [[ cat "/proc/stat" | grep '^cpu ' ]],
    3,
    function(widget, stdout)
        local user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice =
            stdout:match("(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s(%d+)%s")

        local total = user + nice + system + idle + iowait + irq + softirq + steal

        local diff_idle = idle - idle_prev
        local diff_total = total - total_prev
        local diff_usage = (1000 * (diff_total - diff_idle) / diff_total + 5) / 10

        widget:set_markup_silently(" " .. tostring(math.floor(diff_usage)) .. "%")

        total_prev = total
        idle_prev = idle
    end
)
return M
