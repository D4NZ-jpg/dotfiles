return {
    'akinsho/toggleterm.nvim',
    lazy = true,
    version = "*",
    keys = {
        { "<leader>tt", "<cmd>ToggleTerm<cr>", desc = "Toggle Terminal" },
    },
    opts = {
        direction = 'float'
    }
}
