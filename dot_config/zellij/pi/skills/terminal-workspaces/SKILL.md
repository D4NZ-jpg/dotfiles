---
name: terminal-workspaces
description: Load when asked to open/run/watch a command in a terminal tab or pane; create or switch a workspace; set a task name; list workspaces/agents or find agents needing attention; or start another Pi. Do not load for ordinary captured shell commands.
---

# Terminal workspaces

Use ZELLIJ and ZELLIJ_SESSION_NAME to identify the current workspace. Do not nest another multiplexer.

## Zellij

A workspace is a session. A task window is a tab with a stable numeric name prefix. A group is metadata, not a separate session hierarchy. The zellij_workspace tool provides:

- list: terminal panes and Pi state across live workspaces.
- attention: asking/done/error/exited agents across workspaces.
- workspace: create/reuse workspace, optional cwd/group/focus.
- open: command argv, optional workspace/cwd/name/note/kind (tab or split), direction (right/down), focus (false by default).
- note: set the shared task name: rename the tab while preserving its numeric slot, and update all pane/Pi labels in that tab. With pane, target that pane's tab, even if inactive. Specify workspace when targeting another session. Empty text resets the name to shell.
- focus: known terminal pane ID, with workspace when targeting another session.

Inspect list before selecting a target; pane IDs repeat across sessions. Ask when the intended workspace is ambiguous. For a fresh Pi use command ["pi"], optionally ["pi", "--", "initial prompt"]. A new Pi is not a continuation or a copy of this thread.

The same controls exist outside Pi through zellij-ws (or the shell ws function):

```
ws workspaces
ws list
ws workspace NAME --dir PATH --group GROUP --focus
ws window --in NAME --dir PATH --name TOOL --note TASK -- command args
ws split --right -- command args
ws pi --in NAME --dir PATH --note TASK [initial prompt]
note task description
```

Zellij cannot transfer running panes/tabs between sessions. Do not approximate a move by killing/restarting a command. ws move fails explicitly without changing anything.

Only open agents/tools when the user requests them. Do not close tabs, panes, sessions, or unrelated terminals. Do not read transcripts, credentials, provider settings, or browser profiles for workspace control. Do not reorder tabs or workspaces by agent status.

If the tool is missing in a Zellij Pi instance, ask for /reload or a fresh Pi. The helper may also be used through Bash. Outside Zellij, ask the user to open a workspace rather than nesting another multiplexer.
