-- Ctrl+w h/j/k/l stay Vim's own window motions; when there is no window in
-- that direction, hand the move to the enclosing Zellij pane.
-- Zellij's autolock plugin must let Ctrl+w reach Vim while Vim is focused.
local function zellij_command()
  if vim.fn.executable("zellij") == 1 then return "zellij" end
  -- Temporary isolated trial: no system-wide binary or PATH changes required.
  local trial = vim.fn.expand("~/.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij")
  if vim.fn.executable(trial) == 1 then return trial end
end
local function navigate(dir)
  return function()
    local before = vim.api.nvim_get_current_win()
    vim.cmd.wincmd(dir)
    if vim.api.nvim_get_current_win() ~= before then return end
    if vim.env.ZELLIJ then
      local command = zellij_command()
      if command then
        local direction = ({ h = "left", j = "down", k = "up", l = "right" })[dir]
        vim.fn.system({ command, "action", "move-focus", direction })
      end
    end
  end
end

for _, dir in ipairs({ "h", "j", "k", "l" }) do
  vim.keymap.set({ "n", "t" }, "<C-w>" .. dir, navigate(dir), { desc = "Window/pane " .. dir })
  -- Treat Alt+hjkl the same way when the editor receives those keys.
  vim.keymap.set({ "n", "t", "i" }, "<M-" .. dir .. ">", navigate(dir), { desc = "Window/pane " .. dir })
end

return {}
