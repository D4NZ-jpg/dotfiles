return {
	"nvim-treesitter/nvim-treesitter",
	build = ":TSUpdate",
	event = { "BufReadPost", "BufNewFile" },
	dependencies = { { "nvim-treesitter/nvim-treesitter-textobjects" } },
	keys = {
		{ "<c-space>", desc = "Increment selection" },
		{ "<bs>", desc = "Schrink selection", mode = "x" },
	},
	opts = {
		highlight = { enable = true },
		indent = { enable = true },
		context_commentstring = { enable = true, enable_autocmd = false },
		ensure_installed = {
			"bash",
			"help",
			"html",
			"javascript",
			"json",
			"lua",
			"markdown",
			"markdown_inline",
			"python",
			"query",
			"regex",
			"tsx",
			"typescript",
			"vim",
			"yaml",
			"cpp",
			"rust",
		},
		incremental_selection = {
			enable = true,
			keymaps = {
				scope_incremental = "<nop>",
				node_decremental = "<bs>",
			},
		},
	},

	config = function(_, opts)
		require("nvim-treesitter.configs").setup(opts)
	end,
}
