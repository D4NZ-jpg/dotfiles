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
        },
        config = function()
            local lsp = require("lsp-zero").preset({})
            local cmp = require("cmp")
            lsp.on_attach(function(_, bufnr)
                lsp.default_keymaps({ buffer = bufnr })
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
                }
            })
            lsp.setup()
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
            dap.adapters.codelldb = {
                type = 'server',
                port = "${port}",
                executable = {
                    command = "codelldb",
                    args = { "--port", "${port}" }
                }
            }

            dap.configurations.cpp = {
                {
                    name = "Launch file",
                    type = "codelldb",
                    request = "launch",
                    program = function()
                        return vim.fn.input('Path to executable: ', vim.fn.getcwd() .. '/', 'file')
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
            }

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
