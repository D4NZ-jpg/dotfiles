return {
    'stevearc/oil.nvim',
    dependencies = { { "nvim-mini/mini.icons", opts = {} } },
    keys = {
        { "-",          "<cmd>Oil --float<cr>", desc = "Open Oil" },
        { "<leader>fo", "<cmd>Oil --float<cr>", desc = "Open filesystem view" },
    },
    opts = {
        columns = {
            "icon",
        },
        watch_for_changes = true,
        keymaps = {
            ["<C-s>"] = { "actions.select", opts = { horizontal = true } },
            ["<C-v>"] = { "actions.select", opts = { vertical = true } },
            ["<C-t>"] = { "actions.select", opts = { tab = true } },
            ["<C-p>"] = "actions.preview",

            ["<C-c>"] = "actions.close",
            ["q"] = "actions.close",

            ["-"] = "actions.parent",
            [".."] = "actions.parent",

            ["<CR>"] = "actions.select",
            ["<C-l>"] = "actions.refresh",
        },
        float = {
            padding = 5,
        },
    },
}
