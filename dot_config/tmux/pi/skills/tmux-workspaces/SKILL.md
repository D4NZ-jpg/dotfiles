---
name: tmux-workspaces
description: Load when the user asks to open, run or watch something in a new window, tab, split or pane; to run an interactive program (dev server, watcher, k9s, lazygit, log tail) alongside the conversation; to start another or parallel pi session; to open, create or switch to a workspace; to move this window elsewhere; to label or annotate this window; or asks which workspaces, windows or pi sessions exist or what is running where. Do not load for ordinary shell commands whose output you need.
---

# tmux workspaces

The user runs pi inside tmux. A **workspace** is a tmux session; a **window**
inside it holds an agent or tool. Everything is done with one command,
`tmux-ws` (on PATH; source in `~/.config/tmux/bin`). Run it through the bash tool.
Every subcommand prints what it did; report that line back.

## See what exists

```
tmux-ws list
```

Prints each workspace (`group/name`) and its windows as
`index:name  pi-state  note  directory`. Use this before targeting a
workspace by name, and to answer "what's running where".

## Run something in a window

```
tmux-ws window [--in WS] [--dir D] [--name N] [--note TEXT] [--focus] <command...>
```

Opens a new window running the command (dev servers, watchers, TUIs, log
tails). Defaults: current workspace, current directory, window named after
the command, note = the command. `--in WS` targets another workspace and
creates it if missing. `--focus` switches there; otherwise the user stays.

```
tmux-ws split [--right|--down] [--dir D] <command...>
```

Same, but as a pane beside the current one (default right). Use for
things the user wants to watch while talking to you.

## Start another pi

```
tmux-ws pi [--in WS] [--dir D] [--name N] [--note TEXT] [--focus] [initial prompt...]
```

Starts a separate pi in a new window, for a parallel thread on another
task or project. The initial prompt is optional. Keep names short; the
window shows pi's own title as its note once it has one.

## Workspaces, notes, moving

```
tmux-ws workspace <name> [--dir D] [--focus]   # create or reuse a workspace
tmux-ws note <text>                            # label this window in the status bar
tmux-ws move <workspace>                       # move this window to another workspace
```

## Rules

- Ask for a target when the user says "there" or "the other one" and
  `tmux-ws list` shows more than one plausible workspace.
- Never close windows or workspaces; the user does that.
- Quote commands with spaces as separate arguments, e.g.
  `tmux-ws window --name dev npm run dev`.
