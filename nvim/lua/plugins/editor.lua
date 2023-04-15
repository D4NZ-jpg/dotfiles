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

    -- tabs
    {
        "nanozuki/tabby.nvim",
        event = "TabNew",
        config = function()
            require("tabby.tabline").use_preset("active_wins_at_tail")
        end,
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
}
