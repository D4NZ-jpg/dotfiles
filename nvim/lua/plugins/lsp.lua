return {

    {
        "VonHeikemen/lsp-zero.nvim",
        branch = "v1.x",
        event = { "BufReadPost", "BufNewFile" },
        dependencies = {
            -- LSP Support
            { "neovim/nvim-lspconfig" },
            { "williamboman/mason.nvim",          config = true },
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
            local lsp = require("lsp-zero").preset({
                name = "recommended",
                set_lsp_keymaps = { preserve_mappings = false },
            })

            lsp.ensure_installed({
                "eslint",
                "lua_ls",
                "rust_analyzer",
            })

            lsp.nvim_workspace()
            lsp.setup()

            require("luasnip.loaders.from_snipmate").lazy_load()
        end,
    },

    -- null-ls
    {
        "jay-babu/mason-null-ls.nvim",
        dependencies = {
            "williamboman/mason.nvim",
            "jose-elias-alvarez/null-ls.nvim",
        },
        event = { "BufReadPost", "BufNewFile" },
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
                },

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
        },
        config = function()
            vim.g.cmake_link_compile_commands = 1
            vim.g.cmake_generate_options = { "-G MinGW Makefiles" }
        end
    }
}
