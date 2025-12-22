return {
    {
        'nvim-treesitter/nvim-treesitter',
        lazy = false,
        build = ':TSUpdate',
        dependencies = {
            {"nvim-treesitter/nvim-treesitter-textobjects", branch = "main"},
        }
    },
}
