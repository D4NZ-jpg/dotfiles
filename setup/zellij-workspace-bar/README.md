# Workspace-labelled native tab bar

This patch changes the bundled Zellij 0.45.1 tab bar's left prefix from `Zellij` to the current session/workspace name. It keeps native tabs, mouse selection, the new-tab button, scroll indicators and breadcrumb navigation. Pane-frame names can stay hidden independently.

Upstream: [zellij-org/zellij](https://github.com/zellij-org/zellij), commit `efd8fd5a89a20c07a111d248ad7fce53848d2c18` (tag `v0.45.1`), MIT license. The installer downloads only `main.rs`, `line.rs`, `tab.rs` and the license, checks `upstream.sha256`, then applies `workspace-name.patch`. No compiled binary is tracked.

Build/install from the chezmoi source directory:

```sh
bash setup/scripts/executable_zellij-workspace-bar.sh
```

Rust 1.95.0 and the `wasm32-wasip1` target are isolated under `~/.local/state/dotfiles-review/workspace-bar-build`; the global Rust toolchain is unchanged. `Cargo.lock` pins the complete dependency graph, including Zellij SDK 0.45.1. The installed wasm is `~/.local/share/zellij/plugins/workspace-bar-0.45.1.wasm`. A receipt verifies both build inputs and installed bytes before skipping a rebuild.

The file plugin requests only `ReadApplicationState` and `ChangeApplicationState`, as required to render native state and select tabs. It never requests `RunCommands`. The installer backs up the permission cache before adding/restricting this exact plugin's entry and preserves unrelated entries.

Live layout migration must retain existing terminal panes and remove only replaced native bar plugins. Do not replay terminal commands or restart agents to change the UI.
