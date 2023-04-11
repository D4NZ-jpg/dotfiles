return {

	-- file browser
	{
		"nvim-telescope/telescope-file-browser.nvim",
		dependencies = { "nvim-telescope/telescope.nvim", "nvim-lua/plenary.nvim", "nvim-tree/nvim-web-devicons" },
	},

	-- telescope
	{
		"nvim-telescope/telescope.nvim",
		dependencies = { "nvim-lua/plenary.nvim", "nvim-tree/nvim-web-devicons" },
		cmd = "Telescope",
		opts = {
			defaults = {
				file_ignore_patterns = { "^.git/", "^node_modules/", "^vendor/" },
			},
			extensions = {
				file_browser = {
					hijack_netrw = true,
				},
			},
		},

		config = function(_, opts)
			require("telescope").setup(opts)
			require("telescope").load_extension("file_browser")
		end,

		keys = {
			{ "<leader>:", "<cmd>Telescope command_history<cr>", desc = "Command History" },
		},
	},

	-- which-key
	{
		"folke/which-key.nvim",
		event = "VeryLazy",
		config = function()
			vim.o.timeout = true
			vim.o.timeoutlen = 300
			local wk = require("which-key")
			wk.setup()
			wk.register(require("core.keymaps"))
		end,
	},

	-- undotree
	{
		"mbbill/undotree",
		event = { "BufReadPost", "BufNewFile" },
		keys = { { "<leader>l", "<cmd>UndotreeToggle<cr>", desc = "Toggle undotree" } },
	},

	-- git
	{
		"tpope/vim-fugitive",
		event = "VeryLazy",
	},

	-- git diff
	{
		"sindrets/diffview.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		event = "VeryLazy",
	},

	-- tabs
	{
		"nanozuki/tabby.nvim",
		event = "VeryLazy",
		config = function()
			require("tabby.tabline").use_preset("active_wins_at_tail")
		end,
	},

	-- easy buffer moving
	{
		"ggandor/leap.nvim",
		event = { "BufReadPost", "BufNewFile" },
		dependencies = { "tpope/vim-repeat" },
		config = function()
			require("leap").add_default_mappings()
		end,
		keys = { "s" },
	},

	-- fast comments
	{
		"numToStr/Comment.nvim",
		event = { "BufNewFile", "BufReadPost" },
		config = true,
		keys = { { "gc", mode = "x" }, { "gb", mode = "x" } },
	},

	--autopairs
	{
		"windwp/nvim-autopairs",
		config = true,
		event = { "BufReadPost", "BufNewFile" },
	},

	-- trouble
	{
		"folke/trouble.nvim",
		event = { "BufReadPost", "BufNewFile" },
		dependencies = { "nvim-tree/nvim-web-devicons" },
		config = true,
	},

	-- fold indents
	{
		"anuvyklack/pretty-fold.nvim",
		event = { "BufReadPost", "BufNewFile" },
	},  

	-- mkdir
	{
		"jghauser/mkdir.nvim",
		event = "VeryLazy",
	},

	-- Better Term
	{
		"CRAG666/betterTerm.nvim",
		config = true,
	},

	-- todo comments
	{
		"folke/todo-comments.nvim",
		config = true,
		event = { "BufReadPost", "BufNewFile" },
	},

 }
