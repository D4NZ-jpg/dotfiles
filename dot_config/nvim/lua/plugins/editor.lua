return {
    -- snacks 
    {
        "folke/snacks.nvim",
        priority = 1000,
        lazy = false,
        opts = {
            quickfile = {
                enabled = true
            }
        }
    },

    -- telescope & file browser
    {
        "nvim-telescope/telescope.nvim",
        dependencies = { "nvim-lua/plenary.nvim", "nvim-tree/nvim-web-devicons",
            "nvim-telescope/telescope-file-browser.nvim" },
        cmd = "Telescope",
        opts = {
            defaults = {
                file_ignore_patterns = { ".git/.*", "node_modules/.*" },
            },
            extensions = {
                file_browser = {
                    hijack_netrw = true,
                },
            },
        },
        config = function(_, opts)
            require("telescope").setup(opts)
            require("telescope").load_extension("file_browser")
        end,
    },

    -- which-key
    {
        "folke/which-key.nvim",
        event = "VeryLazy",
        config = function()
            vim.o.timeout = true
            vim.o.timeoutlen = 300
            local wk = require("which-key")
            wk.setup()
            wk.register(require("core.keymaps"))
        end,
    },

    -- undotree
    {
        "mbbill/undotree",
        keys = { { "<leader>l", "<cmd>UndotreeToggle<cr>", desc = "Toggle undotree" } },
    },

    -- git diff
    {
        "sindrets/diffview.nvim",
        dependencies = { "nvim-lua/plenary.nvim" },
        keys = {
            { "<leader>gd", "<cmd>DiffviewOpen<cr>", desc = "Show git differences" }
        },
        cmd = "DiffviewOpen"
    },

    -- fast moving around file
    {
        "ggandor/leap.nvim",
        dependencies = { "tpope/vim-repeat" },
        config = function()
            require("leap").add_default_mappings()
        end,
        keys = { "s", "S" },
    },

    -- fast comments
    {
        "numToStr/Comment.nvim",
        config = true,
        keys = { "gc", "gb" },
    },

    --autopairs
    {
        "windwp/nvim-autopairs",
        config = true,
        event = "InsertEnter",
    },

    -- trouble
    {
        "folke/trouble.nvim",
        opts = {
            warn_no_results = false,
            open_no_results = true,
        },
        cmd = "Trouble",
        keys = {
            {
                "<leader>xx",
                "<cmd>Trouble diagnostics toggle<cr>",
                desc = "Diagnostics (Trouble)",
            },
            {
                "<leader>xX",
                "<cmd>Trouble diagnostics toggle filter.buf=0<cr>",
                desc = "Buffer Diagnostics (Trouble)",
            },
            {
                "<leader>cs",
                "<cmd>Trouble symbols toggle focus=false<cr>",
                desc = "Symbols (Trouble)",
            },
            {
                "<leader>cl",
                "<cmd>Trouble lsp toggle focus=false win.position=right<cr>",
                desc = "LSP Definitions / references / ... (Trouble)",
            },
            {
                "<leader>xL",
                "<cmd>Trouble loclist toggle<cr>",
                desc = "Location List (Trouble)",
            },
            {
                "<leader>xQ",
                "<cmd>Trouble qflist toggle<cr>",
                desc = "Quickfix List (Trouble)",
            },
        },
    },

    -- mkdir
    {
        "jghauser/mkdir.nvim",
        event = "BufNewFile",
    },

    -- Better Term
    {
        "CRAG666/betterTerm.nvim",
        config = true,
        keys = {
            { "<leader>t", "<cmd>lua require('betterTerm').open()<cr>", desc = "Toggle terminal" }
        }
    },

    -- Show colors
    {
        "brenoprata10/nvim-highlight-colors",
        config = true,
        ft = { "html", "css", "scss", "sass", "svelte" }
    },

    -- color current window border
    {
        "nvim-zh/colorful-winsep.nvim",
        event = "WinNew",
        config = true
    },

    -- buffer file editor
    {
        "stevearc/oil.nvim",
        config = true,
        dependencies = { "nvim-tree/nvim-web-devicons" },
        keys = {
            { "-", "<cmd>lua require('oil').open()<cr>", desc = "Open parent directory" }
        }
    },

    -- code outline
    {
        'stevearc/aerial.nvim',
        dependencies = {
            "nvim-treesitter/nvim-treesitter",
            "nvim-tree/nvim-web-devicons"
        },
        config = true,
        keys = {
            { "<leader>a", "<cmd>AerialToggle!<CR>", desc = "Toggle Aerial (Outline)" }
        }
    },
}
