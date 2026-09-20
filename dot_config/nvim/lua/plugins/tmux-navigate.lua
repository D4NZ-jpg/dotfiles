-- Ctrl+w h/j/k/l stay Vim's own window motions; when there is no window in
-- that direction and we are inside tmux, hand the move to the tmux pane.
-- Nothing else changes, so stock vim muscle memory still applies.
local function navigate(dir)
  return function()
    local before = vim.api.nvim_get_current_win()
    vim.cmd.wincmd(dir)
    if vim.api.nvim_get_current_win() == before and vim.env.TMUX then
      local flag = ({ h = "-L", j = "-D", k = "-U", l = "-R" })[dir]
      vim.fn.system({ "tmux", "select-pane", flag })
    end
  end
end

for _, dir in ipairs({ "h", "j", "k", "l" }) do
  vim.keymap.set({ "n", "t" }, "<C-w>" .. dir, navigate(dir), { desc = "Window/pane " .. dir })
  -- tmux forwards Alt+hjkl into a vim pane; treat them the same way
  vim.keymap.set({ "n", "t", "i" }, "<M-" .. dir .. ">", navigate(dir), { desc = "Window/pane " .. dir })
end

return {}
