return {
    "folke/which-key.nvim",
    event = "VeryLazy",
    opts = {
        spec = {
            { "g", group = "goto" },
            { "[", group = "prev" },
            { "]", group = "next" },
            { "z", group = "fold" },

            { "<leader>f", group = "Telescope" },
            { "<leader>q", group = "quit/session" },
            { "<leader>s", group = "search" },
            { "<leader>a", group = "AI Assistant" },
            { "<leader>w", group = "windows/workspaces" },
            { "<leader>x", group = "diagnostics/quickfix" },
            { "<leader>c", group = "code" },
            { "<leader>g", group = "git" },
            { "<leader>t", group = "tests" },
        },
    },
}
