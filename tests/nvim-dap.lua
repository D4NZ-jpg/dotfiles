-- Run: lua tests/nvim-dap.lua /path/to/nvim/config
local root = assert(arg[1], "Neovim configuration root required")
local passed = 0
for _, adapter_first in ipairs({ true, false }) do
    local level
    local dap = {
        adapters = {},
        listeners = { after = { event_initialized = {} }, before = { event_terminated = {}, event_exited = {} } },
        set_log_level = function(value) level = value end,
    }
    local available = {}
    vim = {
        fn = {
            stdpath = function() return '/synthetic/data' end,
            getcwd = function() return '/synthetic/project' end,
            executable = function(path) return available[path] and 1 or 0 end,
            has = function() return 1 end,
        },
    }
    package.loaded.dap = dap
    package.loaded.dapui = { setup = function() end, open = function() end, close = function() end }
    package.loaded['nvim-dap-virtual-text'] = { setup = function() end }
    package.loaded['mason-nvim-dap'] = {
        default_setup = function(config) dap.adapters.python = config.adapters end,
    }
    local spec = dofile(root .. '/lua/plugins/lsp/dap.lua')
    local handler = spec.dependencies[1].opts.handlers.python
    local config = {}
    if adapter_first then handler(config); spec.config() else
        spec.config()
        assert(dap.adapters.debugpy == nil)
        handler(config)
    end
    assert(level == 'INFO')
    assert(dap.adapters.python ~= nil and dap.adapters.debugpy == dap.adapters.python)
    assert(dap.adapters.python.command == '/synthetic/data/mason/packages/debugpy/venv/bin/python')
    local python = config.configurations[1].pythonPath
    assert(python() == '/usr/bin/python3')
    available['/synthetic/project/venv/bin/python'] = true
    assert(python() == '/synthetic/project/venv/bin/python')
    available['/synthetic/project/.venv/bin/python'] = true
    assert(python() == '/synthetic/project/.venv/bin/python')
    passed = passed + 1
end
print(passed .. ' DAP load-order tests passed (logging, adapter alias, interpreter selection)')
