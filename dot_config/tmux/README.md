# tmux workspaces

A workspace is a tmux session you name (default: the directory it was opened
from); its windows are agents and tools, each in whatever directory you chose.
One workspace can therefore be a project, or a topic like a review batch with
one window per PR worktree. Positions never move on their own: sessions keep creation order,
windows keep their index. Each window can carry a one-line note that shows in
the status line, so the bar reads like `2:pi · fixing auth redirect ●` where
`●` means the agent has been silent for 20 s and is waiting for you.

Every kitty window lands inside tmux (`shell` in kitty.conf runs
`bin/tmux-attach`): it attaches to the last used workspace or starts `home`.

Prefix is `Ctrl+Space`.

## Moving

| Keys | Action |
| --- | --- |
| `Alt+1..9` | window by index (no prefix) |
| `Alt+Tab` | last window |
| `prefix h` / `prefix l` | previous / next window |
| `` Alt+` `` | last workspace |
| `Alt+h/j/k/l` | pane left/down/up/right |
| `prefix s` | switch workspace (open ones, creation order); `d` closes (asks), `r` renames, `m` sets the group |
| `prefix o` | **open** a workspace: browse from `~/dev` (`h` at the top goes to `~`), dotfiles, Notes; then name it |
| `prefix C` | new window in a chosen directory (same browser) inside this workspace |
| `prefix w` | tree of every workspace and window with notes |
| `prefix g` | windows waiting for you: pi sessions that are asking (`?`), finished (`●`) or errored (`!`), plus tracked non-pi windows that went silent or rang; Enter jumps |
| `prefix G` | **fleet**: every pi session across workspaces with state, age and title; Enter jumps, preview shows the pane |

All pickers are modal, vim style: `j`/`k` move, `g`/`G` first/last,
`Ctrl+d`/`Ctrl+u` half page, `/` enters search (type to filter, Esc returns
to normal mode keeping the match), `q` or Esc quits. In the open-project
browser `l` descends into a directory, `h` goes up, Enter opens the
highlighted directory as the workspace, `z` jumps through zoxide.

## Notes and attention

| Keys | Action |
| --- | --- |
| `prefix n` | set the note for this window (also `note some text` in the shell; `note` alone prints it) |
| (automatic) | a window running `pi` shows pi's session title as its note until you set one yourself |
| `prefix N` | clear the note |
| `prefix a` | mark this window as an agent window: flag after 20 s of silence |
| `prefix A` | stop tracking this window |

## Panes like Vim windows

`Ctrl+w` works the way it does in Vim, in any pane:

| Keys | Action |
| --- | --- |
| `Ctrl+w h/j/k/l` | move to the pane in that direction |
| `Ctrl+w s` / `v` | split below / right (same directory) |
| `Ctrl+w q` / `o` | close this pane / all others |
| `Ctrl+w =` | tile evenly |
| `Ctrl+w H/J/K/L` | swap the pane in that direction |
| `Ctrl+w w` / `p` | next / previous pane |
| `Ctrl+w z` | zoom toggle |
| `Ctrl+w Ctrl+w` | send a literal Ctrl+w to the shell (delete word) |

When the pane runs Neovim, `Ctrl+w` goes to Neovim untouched, so its own
window commands apply; `Ctrl+w h/j/k/l` at the edge of the last window
jumps to the neighbouring tmux pane (`nvim/lua/plugins/tmux-navigate.lua`).
`Alt+h/j/k/l` still move panes and are forwarded into Neovim the same way.
Stock vim without the plugin just stops at its edge.

## Across reboots

The status line snapshots the layout every few seconds
(`tmux-persist save` → `~/.local/state/tmux/workspaces.tsv`): workspaces,
groups, window names and positions, directories, notes, and for pi windows
the exact session file. When kitty starts and no tmux server exists,
`tmux-attach` runs `tmux-persist restore` first: every workspace comes back
and each pi window resumes its own thread with `pi --session <file>`, so
several pi sessions in the same directory each get the right one. If a
session file was deleted, that window starts a fresh pi in the same
directory. Pane splits inside a window are not saved.

`tmux-persist show` prints the snapshot.

## Pi state

The pi extension publishes each session's state to its window, shown as a
marker after the note and in the fleet view:

| Marker | State | Meaning |
| --- | --- | --- |
| `?` | asking | pi is waiting on a prompt (confirm/select/input) |
| `!` | error | the last run ended with an error |
| `●` | done | pi finished and is waiting for your next message |
| `…` | working | pi is running |
| `·` | idle | started, nothing sent yet |

Both lists (`prefix g` and `prefix G`) also show pi's last message, or the
open prompt's title, so you can triage without switching. The bar's right
side counts the states (`?1 ●2 …3`). Windows tracked with
`prefix a` but not running pi use tmux's silence flag instead.

Desktop notifications for pi windows come from the extension too, with the
real text: `workspace · note — done` and pi's last message, `— needs an
answer` with the prompt title, or `— error` (critical) with the error. They
only fire when that window is not the one on screen. Windows tracked with
`prefix a` still get the silence/bell notification with their last line.

Agent tracking is per window because a plain shell prompt is always
"silent". `pi` turns it on by itself through the `pi/tmux-note.ts` extension
(symlinked into `~/.pi/agent/extensions`), which also mirrors the session
title into the window note; a manual note always wins. For other agents use
`prefix a`. When flagged, the
window turns warm in the bar, the right side lists waiting workspaces, and a
Dunst notification shows the pane's last line (one per window per 3 min;
visiting the window resets it). Pi windows skip this: the extension sends
its own notification with the real message (see "Pi state").

## Windows and panes

| Keys | Action |
| --- | --- |
| `prefix c` | new window in the current directory |
| `prefix -` / `prefix \|` | split below / right |
| `prefix ,` | rename window |
| `prefix M` | move this window to another workspace (picker; type a new name to create) |
| `prefix x` / `prefix X` | kill pane / window (confirm) |
| `prefix d` | detach |
| `prefix [` | copy mode (vi keys, `y` copies to the Wayland clipboard) |
| `prefix r` | reload config |

## Scripting and pi

`tmux-ws` (also on PATH) drives everything from a shell or from pi:

```
tmux-ws list                                  workspaces and windows with notes and pi state
tmux-ws window [--in WS] [--dir D] [--name N] [--note T] [--focus] <cmd...>
tmux-ws split [--right|--down] [--dir D] <cmd...>
tmux-ws pi [--in WS] [--dir D] [--name N] [--focus] [prompt...]
tmux-ws workspace <name> [--dir D] [--focus]
tmux-ws note <text>
tmux-ws move <workspace>
```

`--in` targets another workspace and creates it if needed. Pi gets these
through the `tmux-workspaces` skill (`pi/skills/`, symlinked into
`~/.pi/agent/skills`), which only loads when you ask it to open, run, split,
move or list something, or to start a parallel pi.

Helpers in `bin/`: `tmux-attach`, `tmux-pick`, `tmux-open`, `tmux-move`,
`tmux-agent`, `tmux-attention`, `tmux-fleet`, `tmux-ws`, `tmux-persist`,
`fzf-modal.sh`. No plugins; needs tmux ≥ 3.3, fzf, zoxide, notify-send.
