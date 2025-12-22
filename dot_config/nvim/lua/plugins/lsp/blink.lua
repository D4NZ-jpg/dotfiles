return {
    "saghen/blink.cmp",
    version = "1.*",
    event = "InsertEnter",
    lazy = true,
    dependencies = {
        {
        "mikavilpas/blink-ripgrep.nvim",
        version = "*",
        },
        { "moyiz/blink-emoji.nvim" },
    },

    opts = {
		keymap = {
			preset = "default",
		},

		sources = {
			default = { "lsp", "buffer", "ripgrep", "path", "snippets", "lazydev", "emoji" },
			providers = {
                lsp = { module = 'blink.cmp.sources.lsp', score_offset = 100 },
				lazydev = { module = "lazydev.integrations.blink", score_offset = 100 },
                ripgrep = {
                    module = "blink-ripgrep",
                    name = "Ripgrep",
                    opts = {
                        backend = {
                            use = "gitgrep-or-ripgrep"
                        }
                    },
                },
                emoji = {
                    module = "blink-emoji",
                    name = "Emoji",
                }
			},
		},

		snippets = { preset = "luasnip" },

		-- Blink.cmp includes an optional, rbcommended rust fuzzy matcher,
		-- which automatically downloads a prebuilt binary when enabled.
        fuzzy = { implementation = "prefer_rust_with_warning" },

		-- Shows a signature help window while you type arguments for a function
		signature = { enabled = true },

		appearance = {
			nerd_font_variant = "mono",
		},

		completion = {
			-- By default, you may press `<c-space>` to show the documentation.
			documentation = { auto_show = true, auto_show_delay_ms = 500 },
			ghost_text = { enabled = true },
			menu = {
				draw = {
					columns = { { "kind_icon" }, { "label", "label_description", gap = 1 }, { "source_name" } },
					components = {
						source_name = {
							width = { max = 30 },
							text = function(ctx)
								return "[" .. ctx.source_name .. "]"
							end,
							highlight = "BlinkCmpSource",
						},
					},
				},
			},
		},
	},

}
