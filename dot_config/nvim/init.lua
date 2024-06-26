-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable",
        lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

local opts = {
    concurrency = 5,
    dev = {
        path = "~/dev/work",
        patterns = { "D4NZ-jpg" },
        fallback = true
    }
}

require("core.options")
require("core.keymaps")
require("lazy").setup("plugins", opts)
