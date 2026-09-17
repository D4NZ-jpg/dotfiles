return {
    "mfussenegger/nvim-dap",
    event = "LspAttach",
    dependencies = {
        {
            "jay-babu/mason-nvim-dap.nvim",
            dependencies = { "mason-org/mason.nvim" },
            opts = {
                ensure_installed = { "python" },
                automatic_installation = true,
                handlers = {
                    python = function(config)
                        config.adapters = {
                            type = "executable",
                            command = vim.fn.stdpath("data") .. "/mason/packages/debugpy/venv/bin/python",
                            args = { "-m", "debugpy.adapter" },
                        }
                        config.configurations = {
                            {
                                type = "python",
                                request = "launch",
                                name = "Launch file",
                                program = "${file}",
                                pythonPath = function()
                                    local cwd = vim.fn.getcwd()
                                    if vim.fn.executable(cwd .. '/.venv/bin/python') == 1 then
                                        return cwd .. '/.venv/bin/python'
                                    elseif vim.fn.executable(cwd .. '/venv/bin/python') == 1 then
                                        return cwd .. '/venv/bin/python'
                                    else
                                        return '/usr/bin/python3'
                                    end
                                end,
                            },
                        }
                        require('mason-nvim-dap').default_setup(config)
                        -- Also runs when Mason finishes installing debugpy later.
                        local dap = require('dap')
                        dap.adapters.debugpy = dap.adapters.python
                    end,
                },
            },
        },
        "rcarriga/nvim-dap-ui",
        "nvim-neotest/nvim-nio",
        "theHamsta/nvim-dap-virtual-text",
    },
    keys = {
        { "<leader>db", function() require("dap").toggle_breakpoint() end, desc = "DAP: toggle breakpoint" },
        { "<leader>dc", function() require("dap").continue() end,          desc = "DAP: continue" },
        { "<leader>di", function() require("dap").step_into() end,         desc = "DAP: step into" },
        { "<leader>do", function() require("dap").step_over() end,         desc = "DAP: step over" },
        { "<leader>dO", function() require("dap").step_out() end,          desc = "DAP: step out" },
        { "<leader>dr", function() require("dap").repl.toggle() end,       desc = "DAP: toggle REPL" },
        { "<leader>dl", function() require("dap").run_last() end,          desc = "DAP: run last" },
        { "<leader>du", function() require("dapui").toggle() end,          desc = "DAP: toggle UI" },
    },
    config = function()
        local dap = require("dap")
        local dapui = require("dapui")

        dap.set_log_level("INFO")

        dapui.setup()

        require("nvim-dap-virtual-text").setup({
            virt_text_pos = vim.fn.has('nvim-0.10') == 1 and 'inline' or 'eol',
        })

        -- Auto-open/close dapui when debugging starts/ends
        dap.listeners.after.event_initialized["dapui_config"] = function()
            dapui.open()
        end
        dap.listeners.before.event_terminated["dapui_config"] = function()
            dapui.close()
        end
        dap.listeners.before.event_exited["dapui_config"] = function()
            dapui.close()
        end

    end
}
