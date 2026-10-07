-- Run from the chezmoi source root: lua tests/nvim-navigation.lua
local source = "dot_config/nvim/lua/plugins/zellij-navigate.lua"
local maps, calls, window, next_window, executables = {}, {}, 1, 1, {}
local trial = "/trial/zellij"
vim = {
  env = {},
  api = { nvim_get_current_win = function() return window end },
  cmd = { wincmd = function() window = next_window end },
  fn = {
    executable = function(command) return executables[command] and 1 or 0 end,
    expand = function() return trial end,
    system = function(command) calls[#calls + 1] = command end,
  },
  keymap = { set = function(_, key, callback) maps[key] = callback end },
}
dofile(source)
local count = 0
local function check(env, bins, direction, changes_window, expected)
  vim.env, executables, calls = env, bins, {}
  window, next_window = 1, changes_window and 2 or 1
  maps["<C-w>" .. direction]()
  if expected then
    assert(#calls == 1, "expected one backend command")
    assert(table.concat(calls[1], " ") == table.concat(expected, " "), "wrong backend command")
  else
    assert(#calls == 0, "unexpected backend command")
  end
  count = count + 1
end
local directions = { h = "left", j = "down", k = "up", l = "right" }
for _, dir in ipairs({ "h", "j", "k", "l" }) do
  check({ TMUX = "yes" }, {}, dir, false, nil)
  check({ ZELLIJ = "0" }, { zellij = true }, dir, false, { "zellij", "action", "move-focus", directions[dir] })
  check({ ZELLIJ = "0", TMUX = "outer" }, { zellij = true }, dir, false, { "zellij", "action", "move-focus", directions[dir] })
  check({ ZELLIJ = "0" }, { [trial] = true }, dir, false, { trial, "action", "move-focus", directions[dir] })
  check({ ZELLIJ = "0" }, {}, dir, false, nil)
  check({ TMUX = "yes" }, {}, dir, true, nil)
  check({ ZELLIJ = "0" }, { zellij = true }, dir, true, nil)
  check({}, {}, dir, false, nil)
end
assert(maps["<M-h>"] and maps["<M-j>"] and maps["<M-k>"] and maps["<M-l>"])
print(count .. " navigation checks passed")
