-- Disable arrows to force use of hjkl
vim.keymap.set("n", "<Up>", "<nop>")
vim.keymap.set("n", "<Down>", "<nop>")
vim.keymap.set("n", "<Left>", "<nop>")
vim.keymap.set("n", "<Right>", "<nop>")

vim.keymap.set("v", "J", ":m '>+1<cr>gv=gv") -- Move selection up
vim.keymap.set("v", "K", ":m '<-2<cr>gv=gv") -- Move selection down

vim.keymap.set("n", "J", "mzJ`z")            -- Bring next line to the end of the current one without moving the cursor

vim.keymap.set("n", "Q", "<nop>")            -- Disable Q

-- Move to errors
vim.keymap.set("n", "<C-k>", "<cmd>cnext<cr>zz")
vim.keymap.set("n", "<C-j>", "<cmd>cprev<cr>zz")

-- Move between snippet parameters
vim.keymap.set("i", "<C-k>", "<cmd>lua require('luasnip').jump(1)<cr>")
vim.keymap.set("i", "<C-j>", "<cmd>lua require('luasnip').jump(-1)<cr>")

-- Terminal
vim.keymap.set("t", "<C-q>", "<C-\\><C-n>")
vim.keymap.set("t", "<A-h>", "<C-\\><C-n><C-w>h")
vim.keymap.set("t", "<A-j>", "<C-\\><C-n><C-w>j")
vim.keymap.set("t", "<A-k>", "<C-\\><C-n><C-w>k")
vim.keymap.set("t", "<A-l>", "<C-\\><C-n><C-w>l")

return {
    { "<C-t>",      group = "Tabs" },
    { "<C-t>a",     "<cmd>tabnew<cr>",                                      desc = "New Tab" },
    { "<C-t>h",     "<cmd>tabp<cr>",                                        desc = "Previous Tab" },
    { "<C-t>l",     "<cmd>tabn<cr>",                                        desc = "Next Tab" },
    { "<C-t>o",     "<cmd>tabonly<cr>",                                     desc = "Close Others" },
    { "<C-t>q",     "<cmd>tabclose<cr>",                                    desc = "Close Tab" },

    { "<C-t>m",     group = "Move" },
    { "<C-t>mh",    "<cmd>-tabmove<cr>",                                    desc = "Move current tab to previous position" },
    { "<C-t>ml",    "<cmd>+tabmove<cr>",                                    desc = "Move current tab to next position" },

    { "<leader>f",  group = "Find" },

    { "<leader>g",  group = "Git" },
    { "<leader>gb", "<cmd>lua Snacks.gitbrowse()<cr>",                      desc = "Open in browser" },
    { "<leader>gg", "<cmd>lua Snacks.lazygit()<cr>",                        desc = "LazyGit" },

    { "<leader>j",  "<cmd>lprev<cr>zz",                                     desc = "Lprev" },
    { "<leader>k",  "<cmd>lnext<cr>zz",                                     desc = "Lnext" },
    { "<leader>r",  ":%s/\\<<C-r><C-w>\\>/<C-r><C-w>/gI<Left><Left><Left>", desc = "Replace current word" },
}

