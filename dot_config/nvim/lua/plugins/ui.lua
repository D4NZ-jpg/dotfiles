return {
    {
        'sainnhe/everforest',
        event = "VimEnter",
        config = function()
            vim.g.everforest_better_performance=1
            vim.g.everforest_transparent_background=2
            vim.cmd.colorscheme('everforest')
        end
    },
 
    -- tabs
    {
        "nanozuki/tabby.nvim",
        event = "TabNewEntered",
        keys = {
            { "<C-t>j", "<cmd>Tabby jump_to_tab<cr>", desc = "Enter tab jump mode"},
        },
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
                fill = 'Normal',
                head = 'MiniTablineCurrent',
                current_tab = 'MiniTablineCurrent',
                inactive_tab = 'MiniTablineVisible',
                win = 'MiniTablineCurrent',
                tail = 'MiniTablineCurrent',
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
                            tab.in_jump_mode() and tab.jump_key() or tab.number(),
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
        "folke/snacks.nvim",
        opts = {
            indent = {
                enabled = true,
                scope = {
                    only_current = true,
                }
            }
        }
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
                    disabled_filetypes = { statusline = { "snacks_dashboard" } },
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

    -- Better notifications
    {
        "folke/snacks.nvim",
        opts = {
            notifier = {
                enabled = true
            }
        }
    },

    -- better ui
    {
        "stevearc/dressing.nvim",
        config = true,
        event = "VeryLazy",
    },

    -- Highlight todo comments
    {
        "folke/todo-comments.nvim",
        dependencies = { "nvim-lua/plenary.nvim" },
        config = true,
        event = "VeryLazy",
    },

    -- dashboard
    {
        "folke/snacks.nvim",
        opts = {
            dashboard = {
                enabled = true,
                preset = {
                    header = [[
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
▒   ▒   ▒▒▒▒▒▒   ▒▒▒▒▒▒▒▒   ▒▒▒▒▒   ▒▒▒▒▒   ▒▒▒▒▒    ▒   ▒   ▒▒
▓▓   ▓▓   ▓▓  ▓▓▓   ▓▓▓   ▓▓   ▓▓▓   ▓▓▓   ▓▓   ▓▓   ▓▓  ▓▓   ▓
▓▓   ▓▓   ▓         ▓▓   ▓▓▓▓   ▓▓▓   ▓   ▓▓▓   ▓▓   ▓▓  ▓▓   ▓
▓▓   ▓▓   ▓  ▓▓▓▓▓▓▓▓▓▓   ▓▓   ▓▓▓▓▓     ▓▓▓▓   ▓▓   ▓▓  ▓▓   ▓
█    ██   ███     ███████   █████████   █████   █    ██  ██   █
███████████████████████████████████████████████████████████████
config by D4NZ-jpg]],
                },
            }
        },
    },
}
