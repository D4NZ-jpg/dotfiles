return {
    -- telescope & file browser
    {
        "nvim-telescope/telescope.nvim",
        dependencies = { "nvim-lua/plenary.nvim", "nvim-tree/nvim-web-devicons",
            "nvim-telescope/telescope-file-browser.nvim" },
        cmd = "Telescope",
        opts = {
            defaults = {
                file_ignore_patterns = { ".git\\", "node_modules\\", "vendor\\" },
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

    -- git
    {
        "tpope/vim-fugitive",
        cmd = { "Git", "G" },
        keys = {
            { "<leader>ga", "<cmd>execute 'G add ' .. input('File: ')<cr>",          desc = "Stage files" },
            { "<leader>gc", "<cmd>execute 'G commit -m ' .. input('Message: ')<cr>", desc = "Commit changes" }
        }
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

    -- lazygit
    {
        "kdheepak/lazygit.nvim",
        cmd = "LazyGit",
        keys = {
            { "<leader>gg", "<cmd>LazyGit<cr>", desc = "Open LazyGit" }
        }
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
        event = { "BufRead", "BufNewFile" },
        dependencies = { "nvim-tree/nvim-web-devicons", { "folke/todo-comments.nvim", config = true } },
        config = true,
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
        ft = { "html", "css", "scss", "sass" }
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

    -- nice notifications
    {
        "rcarriga/nvim-notify",
        event = "VeryLazy",
        opts = {
            background_colour = "#000000",
        },
        config = function(_, opts)
            require("notify").setup(opts)
            vim.notify = require("notify")
        end
    },
}
