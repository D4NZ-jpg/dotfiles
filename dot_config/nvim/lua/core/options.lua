vim.opt.number = true         -- Show line numbers
vim.opt.relativenumber = true -- Show numbers relative to current line
vim.opt.cmdheight = 0         -- Height of command bar

vim.opt.cc = "80"             -- Show column at 80 chars

vim.opt.autoindent = true     -- New line inherits indentation of previous one
vim.opt.expandtab = true      -- Tabs to spaces
vim.opt.tabstop = 4           -- 1 Tab = 4 Spaces
vim.opt.shiftwidth = 4        -- Use 4 spaces when shiftint
vim.opt.shiftround = true     -- When shifting round to nearest
vim.opt.smartindent = true
vim.opt.conceallevel = 1      -- Show concealable characters

vim.opt.tgc = true
vim.opt.clipboard = "unnamedplus"
vim.opt.list = true
vim.opt.listchars:append("eol:↴")
vim.g.mapleader = " "

vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undodir = os.getenv("HOME") .. "/Appdata/local/nvim-data/undotree"
vim.opt.undofile = true

vim.opt.hlsearch = false
vim.opt.incsearch = true

vim.opt.scrolloff = 8
vim.opt.signcolumn = "yes"
vim.opt.isfname:append("@-@")

vim.opt.updatetime = 50

vim.opt.cursorline = true

vim.opt.foldlevel = 99
vim.opt.foldmethod = "expr"
vim.opt.foldexpr = "nvim_treesitter#foldexpr()"
vim.opt.foldenable = false

-- Autocommands
-------------------------------------------------------------------------------

-- Add image filetypes to neovim
vim.cmd([[
  augroup RecognizeImageFiles
    autocmd!
    autocmd BufReadPre *.jpg,*.jpeg,*.png,*.webp,*.gif,*.bmp,*.svg,*.tiff setfiletype image
  augroup END
]])
