-- Disable arrows to force use of hjkl
vim.keymap.set("n", "<Up>", "<nop>")
vim.keymap.set("n", "<Down>", "<nop>")
vim.keymap.set("n", "<Left>", "<nop>")
vim.keymap.set("n", "<Right>", "<nop>")

vim.keymap.set("v", "J", ":m '>+1<cr>gv=gv") -- Move selection up
vim.keymap.set("v", "K", ":m '<-2<cr>gv=gv") -- Move selection down

vim.keymap.set("n", "J", "mzJ`z") -- Bring next line to the end of the current one without moving the cursor

vim.keymap.set("n", "Q", "<nop>") -- Disable Q

-- Move to errors
vim.keymap.set("n", "<C-k>", "<cmd>cnext<cr>zz")
vim.keymap.set("n", "<C-j>", "<cmd>cprev<cr>zz")

-- Add git diff as command
vim.cmd([[command! Diff :DiffviewOpen]])

return {
	["<leader>f"] = {
		name = "+File/Find",
		f = { "<cmd>Telescope find_files<cr>", "Find File" },
		r = { "<cmd>Telescope oldfiles<cr>", "Open Recent File" },
		n = { "<cmd>enew<cr>", "New File" },
		t = { "<cmd>Telescope file_browser<cr>", "Browse Files" },
		h = { "<cmd>Telescope help_tags<cr>", "Help" },
		l = { "<cmd>Telescope live_grep<cr>", "Live Grep" },
	},

	["<C-t>"] = {
		name = "+Tabs",
		a = { "<cmd>$tabnew<cr><cmd>Alpha<cr>", "New Tab" },
		c = { "<cmd>tabclose<cr>", "Close Tab" },
		o = { "<cmd>tabonly<cr>", "Close Others" },
		h = { "<cmd>tabp<cr>", "Previous Tab" },
		l = { "<cmd>tabn<cr>", "Next Tab" },
		g = { "<cmd>execute 'tabn ' .. input('Tab number: ')<cr>", "Jump to tab number" },

		m = {
			name = "+Move",
			h = { "<cmd>-tabmove<cr>", "Move current tab to previous position" },
			l = { "<cmd>+tabmove<cr>", "Move current tab to next position" },
		},
	},

	["<leader>x"] = {
		name = "+Trouble",
		x = { "<cmd>TroubleToggle<cr>", "Toggle Trouble Panel" },
		w = { "<cmd>TroubleToggle workspace_diagnostics<cr>", "Toggle workspace diagnostics" },
		d = { "<cmd>TroubleToggle document_diagnostics<cr>", "Toggle document diagnostics" },
		q = { "<cmd>TroubleToggle loclist<cr>", "Toggle location list" },
		l = { "<cmd>TroubleToggle quickfix<cr>", "Toggle quickfix" },
		r = { "<cmd>TroubleToggle lsp_references<cr>", "Toggle references" },
	},

	["<leader>p"] = { '"_dp', "Void paste", mode = "x" },
	["<leader>k"] = { "<cmd>lnext<cr>zz", "Lnext" },
	["<leader>j"] = { "<cmd>lprev<cr>zz", "Lprev" },
	["<leader>r"] = { ":%s/\\<<C-r><C-w>\\>/<C-r><C-w>/gI<Left><Left><Left>", "Replace current word" },
}
