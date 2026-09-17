-- Keybind adapter only. Workspace allocation and navigation belong to hyprsplit.
local M = {}
function M.new(api, hs)
    local rows = {}
    function rows.step(direction, moving)
        assert(direction == 1 or direction == -1, "invalid workspace direction")
        local monitor = api.get_active_monitor()
        if not monitor or monitor.active_special_workspace or not monitor.active_workspace then return end
        local window = moving and api.get_active_window() or nil
        if moving and (not window or window.pinned or not window.workspace
            or window.workspace.id ~= monitor.active_workspace.id) then return end
        local offset = direction == 1 and "+1" or "-1"
        -- A clamped boundary is a no-op, even if back-and-forth focus is enabled.
        if hs.get_workspace_string(offset) == tostring(monitor.active_workspace.id) then return end
        local dispatcher = moving and hs.dsp.window.move({workspace=offset, follow=true})
            or hs.dsp.focus({workspace=offset})
        local result = api.dispatch(dispatcher)
        assert(result and result.ok, result and result.error or "hyprsplit dispatch failed")
    end
    return rows
end
return M
