# Zellij workspaces

A workspace is a Zellij session. Task windows are tabs; surfaces are panes. Groups and workspace labels are private metadata. Workspace order is creation order, never agent-status order. Workspace renaming in the picker changes the label, not its underlying session ID, so existing shells and agents keep working.

New Kitty windows attach to the last normal workspace. The terminal scratchpad always attaches to its own `scratch` session. Tmux config and helpers are no longer shipped; existing terminal processes are not stopped or moved.

The top bar shows the workspace's native session name at the left instead of `Zellij`. It is a small, source-pinned fork of the bundled tab bar; native tabs and mouse controls are unchanged. Picker labels may differ from the native session name after a rename.

## Keyboard

Prefix is Ctrl+Space, released before the next key.

| Key | Action |
|---|---|
| prefix s | Workspace picker; Alt+R renames, Alt+M sets group, Alt+D removes |
| prefix o | Browse directories and open/create a project workspace |
| prefix w | All workspaces' task panes with notes and status |
| prefix g / G | Agents needing attention / all agents, across workspaces |
| prefix c / C | New task tab here / in a chosen directory |
| prefix n | Set task name; submit an empty name to reset to shell |
| prefix , | Alias for setting the same task name |
| prefix h / l | Previous/next tab |
| Alt+1..9 | Tab by stable numeric slot, not current position |
| Alt+Tab | Last tab |
| Alt+backtick | Last workspace |
| prefix - / pipe | Split down/right |
| prefix z | Fullscreen pane |
| prefix [ | Scrollback; j/k, PageUp/Down, u/d; Esc exits |
| prefix d | Detach without stopping processes |
| prefix r | Save a recovery layout; config itself reloads automatically |

Pickers are centered at 70% of terminal width and 60% of height; note/rename prompts use 60% width and 30% height. They inherit the terminal background, with warm foreground colors and separate action/navigation hints. Geometry is rounded to terminal cells.

Workspace/task/agent pickers use fzf: type to search, arrows or Ctrl+J/K move, Ctrl+U/D scroll half a page, Enter selects, Esc closes.

Alt+D in the workspace picker asks for confirmation, with Cancel selected first. Removal stops that workspace's programs, deletes its native saved session and private workspace layout/metadata, and removes the picker entry. Pi conversation files and historical backups are kept. Switch to another workspace before removing the one you are in. Removal never switches focus to the target; native failures leave its picker entry intact.

The directory picker uses lf: j/k selects, h/l browses parent/child, / searches, Enter chooses the selected directory, . chooses the current directory, q/Esc cancels. Prefix o then asks for the workspace name; prefix C creates a task tab in the chosen directory. Its dedicated directory-only config does not load or modify the normal lf config, clipboard or bookmarks, and disables file-editing and shell-command keys.

A one-row top tab bar shows stable numbered task names and highlights the active tab. No bottom shortcut/status bar is loaded. Default tabs, command tabs and saved recovery layouts retain the top row.

Ctrl+W followed by h/j/k/l moves between panes; s/v splits; w/p selects next/last pane; z fullscreen; H/J/K/L moves panes; q closes the focused pane. Neovim receives its own keys through zellij-autolock and hands focus across editor edges. Approve the plugin's read/change application-state permissions if prompted.

Numeric slot prefixes remain on tab names across resurrection. New slots increase monotonically; closing a tab does not renumber the others. There are no automatic layout changes. Slots above 9 remain accessible through the task tree.

## Shell and Pi

```
ws workspaces
ws list
ws workspace client --dir ~/dev/work/client --group work --focus
ws window --in client --name tests --note 'check auth tests' -- npm test
ws split --down -- lazygit
ws pi --in client --note 'review auth' 'Review the auth changes'
note fixing auth redirect
note                        # show current task note
note ''                     # clear it
```

The same helper is available as `zellij-ws`. The shell `ws`/`note` functions use Zellij.

Pi's optional /znote, /zv, /zh, /zpi, /ztool, /zattention, and /zfleet shortcuts are conveniences, not the workspace interface. Pi's `terminal-workspaces` skill and `zellij_workspace` tool support natural-language control, including creating/opening in another workspace. Use /reload in existing Pi instances; fresh instances load the extension automatically.

A task has one shared name. Ctrl+Space then n, shell note(), and Pi's note tool rename the tab without changing its numeric slot, and update labels for all panes in that tab. Empty text resets it to shell. Pi titles show WORK/ASK/DONE/ERR/IDLE plus that name and a pane ID suffix. Manual task names take priority over automatic session names. Completion uses agent_settled, not agent_end, so retries and compaction do not prematurely mark completion. Killed agents appear as EXIT when the picker refreshes. Notifications contain only a task label and state, not response or prompt text. PI_ZELLIJ_NOTIFY=0 disables these notifications.

Agent pickers (g/G) use aligned Status, Session, Workspace, Last prompt, and Updated columns. Narrow pickers omit Workspace. Agent states use Nerd Font cog, question, check, alert, pause, and close icons alongside their text labels. Status icons retain their color on the selected row, including when NO_COLOR is inherited; these pickers explicitly request a colored fzf base. Status does not change their order. Excerpts come from Pi's user-message events and active branch on reload/switch, not from reading session files; only text is captured, at most 240 characters. Older agents show “No prompt captured” until reloaded. Updated age is the latest published Pi event, not how long the current status has lasted; it refreshes when reopening the picker.

Workspace rows use a console icon for live sessions and an archive icon for saved/exited sessions. Task rows use a robot icon for Pi agents and a console icon for ordinary terminals; identity comes from Pi ownership metadata, not the task name. Numbered tabs, column headings, and keyboard hints remain text.

Alt+S in g snoozes the selected agent's current attention until its next activity. It does not pause or stop Pi. G still shows it with a gray `󰒲` Nerd Font sleep icon; Alt+S there restores it manually. Starting work, a new input request, a changed user prompt, or a different status clears snooze. Renaming or repeating the same completion event does not. If the agent changes while the picker is open, snooze refuses to hide that newer activity. Snooze does not change workspace order or the agent's actual status.

At 90 columns × 22 rows or larger **inside the picker**, the bottom preview shows up to 12 lines of the selected Pi pane's current viewport. It never requests scrollback. Ownership is checked before each preview, and its private temporary index is removed on exit. Smaller pickers omit the preview.

## Remote workspaces over Mosh

Create a workspace with **Ctrl+Space o**. Directory browsing starts on **Local** without a machine-selection prompt. **Alt+M** switches to a configured remote machine; browse its directories, select a path, then enter the workspace name as usual. Both machines use the same isolated lf browser: h/l navigate, j/k select, / searches, Enter selects a directory, and . selects the current directory. Alt+M switches back to Local. Cancel leaves sessions unchanged.

Create `~/.config/zellij/remotes.json` to map picker host labels to SSH accounts, for example `{"dev":"user@dev.example"}`. This machine-specific allowlist is not tracked in Git; without it, only Local is offered. Configure working SSH authentication and trusted host keys separately. Ctrl+Space s lists normal local and remote workspaces with a host label on remote rows; there is no artificial `home · new` entry. g/G and w include remote agents and task panes. Opening a picker or browsing remote paths does not start remote sessions or Pi.

A workspace's selected machine owns its tasks. Ctrl+Space c/C, n, tab navigation, splits, and pane controls operate on that machine. C starts directory selection on the current workspace's machine; choosing another machine creates a workspace there rather than putting a task on the wrong machine. Local workspaces keep their existing behavior.

The remote folder picker runs lf over an SSH TTY with the same dedicated config and layout as Local; only the machine label changes. A one-use private token returns the selection and is removed after consumption. Creation reuses a private SSH connection for browsing, retrieving the selection, creating the workspace, and starting Mosh. It closes that connection before switching clients, or on cancellation/error. The private socket never uses an existing SSH master; saved transports fall back to ordinary SSH once it is gone. An idle master expires after two minutes if cleanup is interrupted. The first authentication can still be delayed. There are no filesystem mounts or persistent picker sessions.

Mosh carries the remote terminal. Its local transport is borderless, with no extra tab bar; the remote server supplies the usual tabs and panes. The outer Zellij retains the unified pickers, while ordinary editor and pane keys pass through to the remote. SSH supplies directory browsing, inventory, labels, task commands, focus, snooze, and bounded viewport previews. It uses your configured SSH agent (including Bitwarden), batch authentication, existing trusted host keys, and no agent or port forwarding. Offline hosts show a hint without hiding local entries. Previously opened legacy transports are not restarted; selecting a remote workspace uses the updated transport, leaving any old connection intact.

Alt+S uses the same ownership/activity guard remotely; stale selections cannot acknowledge newer activity. Remote previews request only the current viewport, never Pi transcripts or scrollback. Remote labels/groups can be changed in s. Remote deletion is deliberately disabled; the existing local confirmation flow is unchanged.

To open or create a named remote workspace explicitly:

```
zellij-ws remote-workspace dev client
```

The remote account needs matching Zellij 0.45.1 helpers under `~/.config/zellij`, a Zellij binary on PATH or in `~/.local/bin`, and `mosh-server`, Python, zsh, fzf, and lf. Install the Pi extension for future remote Pi instances if needed; no existing agent needs to restart. Creating a new remote workspace does not launch Pi. Local Mosh is installed through pacman (`sudo pacman -S --needed mosh`) and is declared in `setup/pkgs/pkgs.lst`. The remote helper uses `/usr/bin/mosh`; `/usr/bin/mosh-client` is provided by the same package. The earlier private wrapper has been retired.

Mosh requires reachable UDP ports (normally 60000–61000); a disposable end-to-end connection was verified. Closing a local Mosh client detaches from remote Zellij rather than stopping remote programs. A dropped connection preserves the current remote workspace. No real remote workspace is started until selected.

Managed remote carriers restore automatically through `remote-attach` for their exact allowlisted host and saved workspace. Restoration creates a fresh SSH/Mosh handshake rather than replaying native `mosh-client` process arguments or old UDP state. The carrier stays borderless, without an extra local tab bar. Temporary SSH control/readiness paths are used only for the current handshake, not durable recovery. Attaching to a carrier with one stopped/held transport pane repairs that pane; running transports and multi-terminal carriers are not replaced.
## Recovery and migration

Private metadata is under ~/.local/state/zellij-workspaces, with mode-0600 files. It holds groups, labels, notes, stable slot counters, Pi session-file pointers, process ownership, event timestamps, and the bounded last prompt for agent pickers. None is tracked in chezmoi. Zellij's scrollback/viewport serialization is disabled.

The legacy tmux snapshot is imported once as workspace/task bookmarks. Pi tasks resume automatically when their workspace is restored. Their restoration helper uses the exact saved Pi session file. It refuses to open a thread still active in tmux or another Zellij pane, or to silently substitute a fresh thread when its file is missing.

Recovery uses native Zellij layouts. Identified Pi panes resume automatically; other commands retain their saved startup behavior. Pi shutdown preserves its exact session-file pointer and restoration token while clearing live-process ownership. Closed Pi panes retain the `· pN` title suffix so agents sharing a task name cannot be confused. Resuming Pi requires a token and exact pointer, not a running process. A saved Pi pane without that identity becomes an ordinary shell at its saved directory, with its Pi arguments and suspension removed; other panes still restore normally. Ambiguous identities are still refused rather than assigned to the wrong conversation. Tokens cannot be reassigned to another conversation file, including when a restored process switches sessions. Before resurrecting an exited session, known Pi commands are rewritten to exact-session wrappers; the original native layout is backed up under restore-backups. Exact-reference Pi restores and managed remote transports run automatically; unrelated commands keep their saved suspension. Helpers also save private recovery layouts on note/task/Pi-state changes. No arbitrary build, server, or shell command is force-run on startup.

Zellij cannot move a running tab/pane between sessions. `ws move` explicitly refuses without restarting anything. tmux-only silence/bell tracking for non-Pi agents, close-other-panes, and equal-tile shortcuts have not been emulated. Tmux config, helpers, Pi links and its package entry are removed from this repo. Existing installed tmux processes are left untouched; the Pi restore guard still checks for an active copy there when tmux is available.

Install the package with `sudo pacman -S zellij`. It is declared in setup/pkgs/pkgs.lst. Until then, this machine's launcher can use the previously verified local trial binary. No binary is tracked. The setup hook installs pinned, checksum-verified zellij-autolock 0.3.0 and builds workspace-bar 0.45.1 from checksum-verified upstream sources with a locked dependency graph. Its Rust/WASI toolchain is isolated from the global toolchain. The workspace bar receives only state-reading and UI-changing permissions, not command execution. Python, fzf, lf, curl and libnotify are existing declared dependencies. See `setup/zellij-workspace-bar/README.md` for the build recipe.

## Validation

From the chezmoi source directory:

```
python tests/zellij-workspaces.py
python tests/zellij-remotes.py
python tests/zellij-ssh-reuse.py
# Opt-in authenticated remote-browser and workspace tests (disposable only):
# Set these to a host/account in your local remotes.json before running:
export ZELLIJ_TEST_REMOTE_HOST=dev
export ZELLIJ_TEST_REMOTE_TARGET=user@dev.example
python tests/zellij-directory-remote.py
python tests/zellij-machine-live.py
python tests/zellij-ssh-reuse-live.py
node tests/zellij-extension.mjs
python tests/zellij-live.py
python tests/zellij-shell-fallback-live.py
python tests/zellij-remote-restore-live.py # fake transport; no SSH, Mosh or Pi launch
python tests/zellij-modals.py
python tests/zellij-top-tabs.py
python tests/zellij-workspace-bar.py
python tests/zellij-directory-picker.py
lua tests/nvim-navigation.lua
```

The integration test uses a private PTY and uniquely named sessions, checks cross-workspace commands, automatic exact-reference Pi recovery and shell fallback, then cleans up only its own sessions. Pi and remote transport executables are harmless test fixtures; no LLM is started. Authenticated remote browser tests require the explicitly configured test host and are not part of the default local checks.
