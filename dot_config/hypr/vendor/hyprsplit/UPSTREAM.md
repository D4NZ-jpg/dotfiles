# Vendored hyprsplit

Source: https://github.com/shezdy/hyprsplit
Commit: `6b00b677d8905fb38779c91e12d6294e0e586a44` (2026-06-11)

`init.lua` is an unmodified upstream copy. The upstream license is in `LICENSE`.
No automatic updates: review/test a new pinned revision before replacing this copy.

Local integration uses 20 slots per monitor, non-persistent workspaces, and the
non-wrapping `+1`/`-1` selectors. `modules/workspace-bindings.lua` only guards
scratchpads, pinned windows and boundary no-ops; it does not implement workspace
allocation. The old custom row manager is not loaded.
