return {
    -- colorscheme
    {
        "folke/tokyonight.nvim",
        config = function()
            vim.cmd([[colorscheme tokyonight]])
        end,
    },

    -- indent guides
    {
        "lukas-reineke/indent-blankline.nvim",
        event = { "BufReadPost", "BufNewFile" },
        config = true,
    },

    -- show current indent
    {
        "echasnovski/mini.indentscope",
        event = { "BufReadPost", "BufNewFile" },
        config = function()
            require("mini.indentscope").setup()
        end,
    },

    -- statusline
    {
        "nvim-lualine/lualine.nvim",
        event = "VeryLazy",
        dependencies = { "SmiteshP/nvim-navic" },
        opts = function(plugin)
            local icons = require("core.config").icons

            local function fg(name)
                return function()
                    ---@type {foreground?:number}?
                    local hl = vim.api.nvim_get_hl_by_name(name, true)
                    return hl and hl.foreground and { fg = string.format("#%06x", hl.foreground) }
                end
            end

            return {
                options = {
                    theme = "tokyonight",
                    globalstatus = true,
                    disabled_filetypes = { statusline = { "alpha" } },
                },
                sections = {
                    lualine_a = { "mode" },
                    lualine_b = { "branch" },
                    lualine_c = {
                        {
                            "diagnostics",
                            symbols = {
                                error = icons.diagnostics.Error,
                                warn = icons.diagnostics.Warn,
                                info = icons.diagnostics.Info,
                                hint = icons.diagnostics.Hint,
                            },
                        },
                        {
                            "filetype",
                            icon_only = true,
                            separator = "",
                            padding = { left = 1, right = 0 },
                        },
                        { "filename", path = 1, symbols = { modified = "  ", readonly = "", unnamed = "" } },
                        -- stylua: ignore
                        {
                            function() return require('nvim-navic').get_location() end,
                            cond = function()
                                return package.loaded['nvim-navic'] and
                                    require('nvim-navic').is_available()
                            end,
                        },
                    },
                    lualine_x = {
                        {
                            require("lazy.status").updates,
                            cond = require("lazy.status").has_updates,
                            color = fg("Special"),
                        },
                        {
                            "diff",
                            symbols = {
                                added = icons.git.added,
                                modified = icons.git.modified,
                                removed = icons.git.removed,
                            },
                        },
                    },
                    lualine_y = {
                        { "progress", separator = " ",                  padding = { left = 1, right = 0 } },
                        { "location", padding = { left = 0, right = 1 } },
                    },
                    lualine_z = {
                        function()
                            return " " .. os.date("%R")
                        end,
                    },
                },
            }
        end,
    },

    -- dashboard
    {
        "goolord/alpha-nvim",
        event = "VimEnter",
        dependencies = {
            "nvim-tree/nvim-web-devicons",
            "MaximilianLloyd/ascii.nvim",
            "MunifTanjim/nui.nvim"
        },
        config = function()
            local function button(sc, label, keybind)
                local sc_ = sc:gsub("%s", ""):gsub("SPC", "<leader>")

                local opts = {
                    position = "center",
                    text = label,
                    shortcut = sc,
                    cursor = 5,
                    width = 44,
                    align_shortcut = "right",
                    hl_shortcut = "AlphaShortcuts",
                    hl = "AlphaHeader",
                }
                if keybind then
                    opts.keymap = { "n", sc_, keybind, { noremap = true, silent = true } }
                end

                return {
                    type = "button",
                    val = label,
                    on_press = function()
                        local key = vim.api.nvim_replace_termcodes(sc_, true, false, true)
                        vim.api.nvim_feedkeys(key, "normal", false)
                    end,
                    opts = opts,
                }
            end

            local header = {
                -- Ascii Header from: https://github.com/glepnir/dashboard-nvim/wiki/Ascii-Header-Text
                type = "text",
                --[[val = {
					"",
					"",
					"⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣠⣤⣤⣴⣦⣤⣤⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
					"⠀⠀⠀⠀⠀⠀⢀⣤⣾⣿⣿⣿⣿⠿⠿⠿⠿⣿⣿⣿⣿⣶⣤⡀⠀⠀⠀⠀⠀⠀ ",
					"⠀⠀⠀⠀⣠⣾⣿⣿⡿⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⢿⣿⣿⣶⡀⠀⠀⠀⠀ ",
					"⠀⠀⠀⣴⣿⣿⠟⠁⠀⠀⠀⣶⣶⣶⣶⡆⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣦⠀⠀⠀ ",
					"⠀⠀⣼⣿⣿⠋⠀⠀⠀⠀⠀⠛⠛⢻⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣧⠀⠀ ",
					"⠀⢸⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⡇⠀ ",
					"⠀⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⠀ ",
					"⠀⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⡟⢹⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⣹⣿⣿⠀ ",
					"⠀⣿⣿⣷⠀⠀⠀⠀⠀⠀⣰⣿⣿⠏⠀⠀⢻⣿⣿⡄⠀⠀⠀⠀⠀⠀⣿⣿⡿⠀ ",
					"⠀⢸⣿⣿⡆⠀⠀⠀⠀⣴⣿⡿⠃⠀⠀⠀⠈⢿⣿⣷⣤⣤⡆⠀⠀⣰⣿⣿⠇⠀ ",
					"⠀⠀⢻⣿⣿⣄⠀⠀⠾⠿⠿⠁⠀⠀⠀⠀⠀⠘⣿⣿⡿⠿⠛⠀⣰⣿⣿⡟⠀⠀ ",
					"⠀⠀⠀⠻⣿⣿⣧⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠏⠀⠀⠀ ",
					"⠀⠀⠀⠀⠈⠻⣿⣿⣷⣤⣄⡀⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⠟⠁⠀⠀⠀⠀ ",
					"⠀⠀⠀⠀⠀⠀⠈⠛⠿⣿⣿⣿⣿⣿⣶⣶⣿⣿⣿⣿⣿⠿⠋⠁⠀⠀⠀⠀⠀⠀ ",
					"⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠛⠛⠛⠛⠛⠛⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ",
				},]]
                val = require('ascii').get_random_global(),
                opts = {
                    position = "center",
                },
            }

            local heading = {
                type = "text",
                val = {
                    " " .. os.date("%d/%m/%y"),
                },
                opts = {
                    position = "center",
                },
            }

            local buttons = {
                type = "group",
                val = {
                    button("e", "  > New File", ":ene <BAR> startinsert <CR>"),
                    button("r", "  > Recent Files", ":Telescope oldfiles<CR>"),
                    button("f", "  > Find File", ":Telescope find_files<CR>"),
                    button("b", "󰥨  > Browse Folders", ":Telescope file_browser<CR>"),
                    button("q", "  > Quit", ":qa<CR>"),
                },
            }

            local footer = {
                type = "text",
                val = "It's not a bug - it's and undocumented feature.",
                opts = {
                    position = "center",
                },
            }

            local config = {
                layout = {
                    { type = "padding", val = 1 },
                    header,
                    { type = "padding", val = 1 },
                    heading,
                    { type = "padding", val = 1 },
                    buttons,
                    { type = "padding", val = 4 },
                    footer,
                },
                opts = {
                    margni = 44,
                },
            }

            require("alpha").setup(config)
        end,
    },
}
