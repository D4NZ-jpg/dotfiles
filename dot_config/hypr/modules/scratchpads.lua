-- Native special-workspace scratchpads; no Pyprland or legacy IPC commands.
local M = {}
local specs = {
    term = { class = "kitty-dropterm", command = "kitty --class kitty-dropterm", width = 0.75, height = 0.60, edge = "top" },
    volume = { class = "pavucontrol", command = "pavucontrol", width = 0.40, height = 0.90, edge = "right", unfocus = true },
    bluetooth = { class = "blueman-manager", command = "blueman-manager", width = 0.40, height = 0.90, edge = "right", unfocus = true },
}
local function run(api, dispatcher)
    local result = api.dispatch(dispatcher)
    assert(result and result.ok, result and result.error or "Scratchpad dispatcher failed")
end
function M.geometry(monitor, spec)
    local reserved = monitor.reserved or {}
    local left, top = reserved.left or 0, reserved.top or 0
    local width, height = monitor.width / monitor.scale, monitor.height / monitor.scale
    if monitor.transform and monitor.transform % 2 == 1 then width, height = height, width end
    width = width - left - (reserved.right or 0)
    height = height - top - (reserved.bottom or 0)
    local w, h = math.floor(width * spec.width), math.floor(height * spec.height)
    local x = spec.edge == "right" and width - w - 10 or (width - w) / 2
    local y = spec.edge == "top" and 10 or (height - h) / 2
    return { x = math.floor(monitor.x + left + x), y = math.floor(monitor.y + top + y), width = w, height = h }
end
function M.new(api)
    local self, pending, busy = {}, {}, false
    local function name_for(window)
        if not window then return nil end
        for name, spec in pairs(specs) do if window.class == spec.class then return name end end
    end
    local function find(name)
        for _, win in ipairs(api.get_windows()) do
            if win.mapped and win.class == specs[name].class then return win end
        end
    end
    local function show(name, window)
        local mon = api.get_active_monitor()
        if not mon then return end
        busy = true
        local ok, err = pcall(function()
            local wsname = "special:pad-" .. name
            if not window.workspace or window.workspace.name ~= wsname then
                run(api, api.dsp.window.move({ window = window, workspace = wsname, follow = false }))
            end
            local visible = mon.active_special_workspace
            if not visible or visible.name ~= wsname then
                run(api, api.dsp.workspace.toggle_special("pad-" .. name))
            end
            local box = M.geometry(mon, specs[name])
            run(api, api.dsp.window.float({ window = window, action = "set" }))
            run(api, api.dsp.window.resize({ window = window, x = box.width, y = box.height }))
            run(api, api.dsp.window.move({ window = window, x = box.x, y = box.y }))
            run(api, api.dsp.focus({ window = window }))
        end)
        busy = false
        if not ok then error(err) end
    end
    function self.toggle(name)
        assert(specs[name], "Unknown scratchpad")
        local mon = api.get_active_monitor()
        if not mon then return end
        local visible = mon.active_special_workspace
        if visible and visible.name == "special:pad-" .. name then
            mon:set_special_workspace({})
            return
        end
        local window = find(name)
        if window then show(name, window); return end
        if pending[name] and pending[name].expires > os.time() then
            pending[name].show = not pending[name].show
            return
        end
        pending[name] = { expires = os.time() + 15, show = true, monitor = mon.name }
        run(api, api.dsp.exec_cmd(specs[name].command))
    end
    for name, spec in pairs(specs) do
        api.window_rule({ name = "scratchpad-" .. name,
            match = { class = "^(" .. spec.class .. ")$" },
            float = true, workspace = "special:pad-" .. name .. " silent" })
        api.workspace_rule({ workspace = "special:pad-" .. name,
            animation = spec.edge == "top" and "slidevert" or "slide" })
    end
    api.on("window.open", function(window)
        local name = name_for(window)
        local request = name and pending[name]
        if not request then return end
        pending[name] = nil
        local mon = api.get_active_monitor()
        -- Do not steal focus back if the user switched monitors while it launched.
        if request.show and request.expires > os.time() and mon and mon.name == request.monitor then
            show(name, window)
        end
    end)
    api.on("window.active", function(window)
        if busy or not window then return end
        for _, mon in ipairs(api.get_monitors()) do
            local special = mon.active_special_workspace
            local name = special and special.name:match("^special:pad%-(.+)$")
            if name and specs[name] and specs[name].unfocus
                and (not window.workspace or window.workspace.name ~= special.name) then
                mon:set_special_workspace({})
            end
        end
    end)
    return self
end
M.specs = specs
return M
