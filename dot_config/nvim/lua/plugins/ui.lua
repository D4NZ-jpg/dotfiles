return {
    -- colorscheme
    {
        "nyoom-engineering/oxocarbon.nvim",
        config = function()
            vim.cmd([[colorscheme oxocarbon]])

            --tabs
            local colors = require("oxocarbon").oxocarbon

            vim.api.nvim_set_hl(0, "TabLineHead", { fg = colors.base00, bg = colors.base09 })
            vim.api.nvim_set_hl(0, "TabLineIna", { fg = colors.base00, bg = colors.base03 })
            vim.api.nvim_set_hl(0, "TabLineFill", { fg = colors.base03, bg = colors.base00 })
        end
    },

    -- transparent background
    {
        "xiyaowong/transparent.nvim",
        config = function()
            vim.g.transparent_enabled = true
        end,
    },

    -- tabs
    {
        "nanozuki/tabby.nvim",
        event = "TabNew",
        config = function()
            local function tab_name(tab)
                return string.gsub(tab, "%[..%]", "")
            end

            local function tab_modified(tab)
                local wins = require("tabby.module.api").get_tab_wins(tab)
                for i, x in pairs(wins) do
                    if vim.bo[vim.api.nvim_win_get_buf(x)].modified then
                        return ""
                    end
                end
                return ""
            end

            local function lsp_diag(buf)
                local diagnostics = vim.diagnostic.get(buf)
                local count = { 0, 0, 0, 0 }

                for _, diagnostic in ipairs(diagnostics) do
                    count[diagnostic.severity] = count[diagnostic.severity] + 1
                end
                if count[1] > 0 then
                    return vim.bo[buf].modified and "" or ""
                elseif count[2] > 0 then
                    return vim.bo[buf].modified and "" or ""
                end
                return vim.bo[buf].modified and "" or ""
            end

            local function buffer_name(buf)
                if string.find(buf, "NvimTree") then
                    return "NvimTree"
                end
                return buf
            end
            local theme = {
                fill = 'TabLineFill',
                head = 'TabLineHead',
                current_tab = 'TabLineHead',
                inactive_tab = 'TabLineIna',
                tab = 'TabLine',
                win = 'TabLineHead',
                tail = 'TabLineHead',
            }

            require('tabby.tabline').set(function(line)
                return {
                    {
                        { '  ', hl = theme.head },
                        line.sep('', theme.head, theme.fill),
                    },
                    line.tabs().foreach(function(tab)
                        local hl = tab.is_current() and theme.current_tab or theme.inactive_tab
                        return {
                            line.sep('', hl, theme.fill),
                            tab.number(),
                            "",
                            tab_name(tab.name()),
                            "",
                            tab_modified(tab.id),
                            line.sep('', hl, theme.fill),
                            hl = hl,
                            margin = ' ',
                        }
                    end),
                    line.spacer(),
                    line.wins_in_tab(line.api.get_current_tab()).foreach(function(win)
                        local hl = win.is_current() and theme.current_tab or theme.inactive_tab
                        return {
                            line.sep('', hl, theme.fill),
                            win.file_icon(),
                            "",
                            buffer_name(win.buf_name()),
                            "",
                            lsp_diag(win.buf().id),
                            line.sep('', hl, theme.fill),
                            hl = hl,
                            margin = ' ',
                        }
                    end),
                    {
                        line.sep('', theme.tail, theme.fill),
                        { '  ', hl = theme.tail },
                    },
                    hl = theme.fill,
                }
            end, {})
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
        event = "VimEnter",
        dependencies = { "SmiteshP/nvim-navic" },
        opts = function()
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
                    button("f", "  > Find File", ":Telescope find_files hidden=true<CR>"),
                    button("b", "󰥨  > Browse Folders", ":Telescope file_browser hidden=true<CR>"),
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

    -- better ui
    {
        "stevearc/dressing.nvim",
        config = true,
        event = "VeryLazy",
    }
}
