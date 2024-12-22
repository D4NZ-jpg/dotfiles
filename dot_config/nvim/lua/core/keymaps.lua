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


-- Add git diff as command
vim.cmd([[command! Diff :DiffviewOpen]])

-- Add shortened commands for Competitest. This is important because these abbreviated commands might not initially seem intuitive.
-- "CP" -> CompetiTest run
-- "CP problem" -> CompetiTest receive problem
-- "CP contest" -> CompetiTest receive contest
vim.cmd([[
"Call the appropriate CompetiTest command
function! s:CompetiTestFunction(arg) abort
    if a:arg == ""
        " Create bin folder if not existing
        if !isdirectory("./bin")
            call mkdir("./bin")
        endif

        execute "CompetiTest run"
    else

        " Create .gitignore to hide input and binary files in telescope 🔭
        if !filereadable(".gitignore")
            call writefile(["testcases\nbin"], ".gitignore")
        endif

        execute 'CompetiTest receive ' . a:arg
    endif
endfunction

"Tab completion of the command with 'contest' or 'problem'
function! s:CompetiTestComplete(...) abort
    let l:options = ['problem', 'contest']
    return join(l:options, "\n")
endfunction

"The actual command
 command! -bar -nargs=? -complete=custom,s:CompetiTestComplete CP call s:CompetiTestFunction(<q-args>)
]])

return {
    ["<leader>f"] = {
        name = "+File/Find",
        f = { "<cmd>Telescope find_files hidden=true<cr>", "Find File" },
        r = { "<cmd>Telescope oldfiles<cr>", "Open Recent File" },
        n = { "<cmd>enew<cr>", "New File" },
        t = { "<cmd>Telescope file_browser hidden=true<cr>", "Browse Files" },
        h = { "<cmd>Telescope help_tags<cr>", "Help" },
        l = { "<cmd>Telescope live_grep<cr>", "Live Grep" },
    },
    ["<C-t>"] = {
        name = "+Tabs",
        a = { "<cmd>$tabnew<cr>", "New Tab" },
        q = { "<cmd>tabclose<cr>", "Close Tab" },
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
    ["<leader>k"] = { "<cmd>lnext<cr>zz", "Lnext" },
    ["<leader>j"] = { "<cmd>lprev<cr>zz", "Lprev" },
    ["<leader>r"] = { ":%s/\\<<C-r><C-w>\\>/<C-r><C-w>/gI<Left><Left><Left>", "Replace current word" },
    ["<leader>c"] = "+CMake",
    ["<leader>g"] = "+Git",
}
