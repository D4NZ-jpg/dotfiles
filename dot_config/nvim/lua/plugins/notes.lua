return {
    {
        "nvim-neorg/neorg",
        build = ":Neorg sync-parsers",
        dependencies = {
            "nvim-lua/plenary.nvim",
            "max397574/neorg-contexts",
            "nvim-neorg/neorg-telescope",
            {
                "lukas-reineke/headlines.nvim",
                dependencies = "nvim-treesitter/nvim-treesitter",
                config = true,
            },
        },
        ft = "norg",
        config = function()
            require("neorg").setup {
                load = {
                    ["core.defaults"] = {},  -- Loads default behaviour
                    ["core.concealer"] = {}, -- Adds pretty icons to your documents
                    ["core.summary"] = {},   -- Summary
                    ["core.dirman"] = {      -- Manages Neorg workspaces
                        config = {
                            workspaces = {
                                notes = "~/notes",
                            },
                        },
                    },
                    ["core.integrations.telescope"] = {}, -- Loads default behaviour
                    ["external.context"] = {},
                },
            }

            vim.opt.conceallevel = 1
            local neorg_callbacks = require("neorg.core.callbacks")
            neorg_callbacks.on_event("core.keybinds.events.enable_keybinds", function(_, keybinds)
                -- Map all the below keybinds only when the "norg" mode is active
                keybinds.map_event_to_mode("norg", {
                    n = { -- Normal mode
                        { "<C-s>", "core.integrations.telescope.find_linkable" },
                        { "<C-i>", "core.pivot.invert-list-type" },
                    },

                    i = { -- Insert mode
                        { "<C-l>",  "core.integrations.telescope.insert_link" },
                        { "<C-CR>", "core.integrations.telescope.insert_file_link" },

                        -- Itero
                        { "<C-O>",  "core.itero.next-iteration" },
                    },
                }, {
                    silent = true,
                    noremap = true,
                })
            end)
        end,
    }
}
