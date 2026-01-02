-- Leader Keys
vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

-- UI Options
vim.opt.number = true         -- Show line numbers
vim.opt.relativenumber = true -- Show numbers relative to current line
vim.opt.cmdheight = 0         -- Height of command bar
vim.opt.cursorline = true     -- Highlight current line
vim.opt.scrolloff = 8         -- Keep 8 lines above/below cursor

-- Text Display
vim.opt.colorcolumn = "80"    -- Show column at 80 chars
vim.opt.list = true           -- Show invisible characters
vim.opt.conceallevel = 1      -- Show concealable characters
vim.opt.termguicolors = true  -- Enable 24-bit RGB colors
vim.opt.listchars:append("eol:↴")

-- Indentation
vim.opt.autoindent = true     -- New line inherits indentation of previous one
vim.opt.expandtab = true      -- Tabs to spaces
vim.opt.tabstop = 4           -- 1 Tab = 4 Spaces
vim.opt.shiftwidth = 4        -- Use 4 spaces when shifting
vim.opt.shiftround = true     -- When shifting round to nearest
vim.opt.smartindent = true    -- Smart auto-indenting

-- Search
vim.opt.hlsearch = false      -- Highlight search results
vim.opt.incsearch = true      -- Incremental search
vim.opt.ignorecase = true     -- Case-insensitive search
vim.opt.smartcase = true      -- Case-insensitive search if no capitals

-- Files
vim.opt.swapfile = true       -- Don't create swap files
vim.opt.backup = false        -- Don't create backup files
vim.opt.undofile = true       -- Enable persistent undo
vim.opt.undodir = vim.fn.stdpath("data") .. "/undo"  -- Undo directory
vim.opt.clipboard = "unnamedplus"  -- Use system clipboard

-- Fold
vim.o.foldlevel = 99

-- Performance
vim.opt.updatetime = 50       -- Faster completion (default 4000ms)

-- File Paths
vim.opt.isfname:append("@-@")  -- Include @ and - in file names
