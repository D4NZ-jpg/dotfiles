return {
    -- images
    {
        -- Remember to download ascii image converter and add it to the path
        -- https://github.com/TheZoraiz/ascii-image-converter/releases
        "samodostal/image.nvim",
        dependencies = { "nvim-lua/plenary.nvim", "m00qek/baleia.nvim" },
        ft = "image",
        opts = {
            render = {
                foreground_color = true,
                background_color = true,
                show_label = true,
                use_dithering = true,
                min_padding = 5,
            },
            events = {
                update_on_nvim_resize = true,
            },
        },
    },

    -- latex to ascii
    {
        "jbyuki/nabla.nvim",
        keys = {
            {
                "<leader>p",
                "<cmd>lua require('nabla').popup({border='rounded'})<cr>",
                desc = "Show math equation in floating window"
            }
        },
    },

    -- markdown
    {
        "jakewvincent/mkdnflow.nvim",
        ft = "markdown",
        opts = {
            perspective = {
                priority = 'root',
                fallback = 'first',
                root_tell = "index.md"
            }
        }
    },

    -- md preview
    {
        "iamcco/markdown-preview.nvim",
        build = "cd app && yarn install",
        ft = "markdown",
        config = function()
            vim.g.mkdp_auto_close = 0
            vim.g.mkdp_refresh_slow = 1
        end
    }
}