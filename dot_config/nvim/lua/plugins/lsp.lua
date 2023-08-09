return {

    {
        "folke/neodev.nvim",
        opts = {
            libtary = {
                plugins = { "nvim-dap-ui" },
                types = true
            }
        }
    },
    {
        "VonHeikemen/lsp-zero.nvim",
        branch = "v2.x",
        event = "InsertEnter",
        dependencies = {
            -- LSP Support
            { "neovim/nvim-lspconfig" },
            {
                "williamboman/mason.nvim",
                config = true,
                build = function()
                    pcall(vim.cmd, "MasonUpdate")
                end,
            },
            { "williamboman/mason-lspconfig.nvim" },

            -- Autocompletion
            { "hrsh7th/nvim-cmp" },
            { "hrsh7th/cmp-nvim-lsp" },
            { "hrsh7th/cmp-buffer" },
            { "hrsh7th/cmp-path" },
            { "saadparwaiz1/cmp_luasnip" },
            { "hrsh7th/cmp-nvim-lua" },

            -- Snippets
            { "L3MON4D3/LuaSnip" },
            { "rafamadriz/friendly-snippets" },

            -- Extras
            { "p00f/clangd_extensions.nvim" }
        },
        config = function()
            local lsp = require("lsp-zero").preset({})
            local cmp = require("cmp")
            lsp.on_attach(function(_, bufnr)
                lsp.default_keymaps({ buffer = bufnr })
                require("clangd_extensions.inlay_hints").setup_autocmd()
                require("clangd_extensions.inlay_hints").set_inlay_hints()
            end)

            require("lspconfig").lua_ls.setup(lsp.nvim_lua_ls())
            require("luasnip.loaders.from_snipmate").lazy_load()

            cmp.setup({
                sources = {
                    { name = "nvim_lsp" },
                    { name = "luasnip" }
                },
                mapping = {
                    ['<tab>'] = cmp.mapping.confirm({ select = true }),
                },
                sorting = {
                    comparators = {
                        require("clangd_extensions.cmp_scores"),
                    }
                }
            })
            lsp.setup()

            -- Since this is lazy loading, it doesn't attach automatically if a file is alredy open
            vim.cmd([[LspStart]])
        end,
    },

    -- null-ls
    {
        "jay-babu/mason-null-ls.nvim",
        dependencies = {
            "williamboman/mason.nvim",
            "jose-elias-alvarez/null-ls.nvim",
        },
        event = "InsertEnter",
        opts = {
            ensure_installed = { "stylelua", "eslint" },
            automatic_setup = true,
        },
        config = function(_, opts)
            require("mason-null-ls").setup(opts)
            handlers = {
                function(source_name, methods)
                    require("mason-null-ls.automatic_setup")(source_name, methods)
                end,
            }

            require("null-ls").setup()
        end,
    },

    -- Configure cmake for c++
    {
        'cdelledonne/vim-cmake',
        keys = {
            {
                "<leader>cg",
                "<cmd>CMakeGenerate build<cr>",
                desc =
                "Generate build system"
            },
            {
                "<leader>cb",
                "<cmd>CMakeBuild <cr>",
                desc =
                "Build project"
            },
            {
                "<leader>cq",
                "<cmd>CMakeClose<cr>",
                desc = "Close Cmake window"
            },
            {
                "<leader>cc",
                "<cmd>CMakeClean<cr>",
                desc = "Remove build system and build files"
            }

        },
        config = function()
            vim.g.cmake_link_compile_commands = 1
            vim.g.cmake_generate_options = { "-G MinGW Makefiles" }
        end
    },

    -- Debug
    {
        "mfussenegger/nvim-dap",
        config = function()
            local dap = require('dap')

            dap.defaults.fallback.external_terminal = {
                command = "kitty",
                args = { '-e' }

            }

            dap.adapters.codelldb = {
                type = 'server',
                port = "${port}",
                executable = {
                    command = "codelldb",
                    args = { "--port", "${port}" }
                },
            }

            dap.configurations.cpp = {
                {
                    name = "Launch file",
                    type = "codelldb",
                    request = "launch",
                    stdio = function()
                        local cwd = vim.fn.getcwd()
                        -- If not CP, normal
                        if not string.find(cwd, "/cp/?") then
                            return nil
                        end


                        -- Get this file's testcases
                        local path = vim.fn.expand("%:p:h") .. "/testcases/*"
                        local files = vim.fn.glob(path, false, true)

                        -- escape pattern
                        local escape_list = { "%", ".", "^", "$", "*", "+", "?", "[", "]", "(", ")", "{", "}", "|", "\\" }
                        local file_pattern = vim.fn.expand("%:t:r")
                        for _, esc in pairs(escape_list) do
                            file_pattern = file_pattern:gsub("%" .. esc, "%%" .. esc)
                        end
                        file_pattern = file_pattern .. ".in(%d+)"

                        -- Get matching files
                        local matching_files = {}

                        for _, file in ipairs(files) do
                            local match = file:match(file_pattern)
                            if match then
                                matching_files[tonumber(match)] = file
                            end
                        end

                        -- Prepare list for inputlist()
                        local file_list = {}
                        for key, _ in pairs(matching_files) do
                            table.insert(file_list, "Testcase #" .. key)
                        end

                        table.sort(file_list)
                        table.insert(file_list, 1, "Select a testcase: ")

                        local choice = vim.fn.inputlist(file_list)

                        -- Return the selected file
                        return { matching_files[choice], nil, nil }
                    end,
                    program = function()
                        -- Check if 'cp' is a parent folder (check the competitest config)
                        local cwd = vim.fn.getcwd()
                        if string.find(cwd, "/cp/?") then
                            local path = vim.fn.expand("%:p:h") .. "/bin/"
                            local file = vim.fn.expand("%:t:r")
                            return path .. file
                        end
                        return vim.fn.input('Path to executable: ', cwd .. '/', 'file')
                    end,
                    cwd = '${workspaceFolder}',
                    stopOnEntry = false,
                },
            }
        end,

        dependencies = {
            {
                "rcarriga/nvim-dap-ui",
                config = function()
                    local dap, dapui = require('dap'), require('dapui')
                    dapui.setup()
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
            },
            {
                "theHamsta/nvim-dap-virtual-text",
                dependencies = { "nvim-treesitter/nvim-treesitter" },
                opts = {
                    higlight_new_as_changed = true,
                    only_first_definition = false,
                    all_references = true,
                }
            },
            "VonHeikemen/lsp-zero.nvim",
        },

        keys = {
            {
                "<leader>ds",
                "<cmd>lua require('dap').continue()<cr>",
                desc =
                "Start/Continue debug session"
            },
            {
                "<leader>dc",
                [[
                <cmd>lua require('dap').terminate()<cr>
                <cmd>lua require('dap').close()<cr>
                <cmd>lua require('dapui').close()<cr>
                ]],
                desc =
                "Terminate debug session"
            },
            {
                "<leader>dt",
                "<cmd>lua require('dap').toggle_breakpoint()<cr>",
                desc =
                "Toggle breakpoint"
            },
            {
                "<leader>di",
                "<cmd>lua require('dap').step_into()<cr>",
                desc = "Step into"
            },
            {
                "<leader>do",
                "<cmd>lua require('dap').step_over()<cr>",
                desc = "Step over"
            },
            {
                "<leader>dr",
                "<cmd>lua require('dap').step_out()<cr>",
                desc = "Step (return) out of function"
            }
        },
    }
}
