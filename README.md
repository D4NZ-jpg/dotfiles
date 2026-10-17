# dotfiles

![Screenshot](screenshots/desktop.png)

Arch Linux, Hyprland, one palette everywhere: charcoal `#262626`, cream
`#d5c8ac`, accent `#d9b090`. Managed with [chezmoi](https://www.chezmoi.io).

## What is here

**Desktop**

- **Hyprland**, configured in Lua (`hypr/hyprland.lua` plus `modules/`):
  hyprsplit per-monitor workspaces, ScrollOverview, static wallpaper.
- **Quickshell** panel: an on-demand top bar with clock, network, volume and
  Bluetooth popups built on Quickshell's own bindings, no external tools
  (`quickshell/panel/README.md`).
- **Rofi** for launcher, emoji, calculator and the power menu
  (Super+Shift+P), with vim keys.
- **Dunst** notifications, **swaylock** on the wallpaper with a script that
  recovers from a monitor Hyprland reports at 0×0, **hypridle**.
- **GTK 3/4** via adw-gtk-theme and a `gtk.css` that maps Adwaita's named
  colours onto the palette; **Qt 5/6** via qt6ct/qt5ct with Fusion and a
  matching colour scheme. Icons are Tela (brown), built by
  `setup/scripts/icons.sh` into `~/.local/share/icons` so only one colour
  variant is installed.

**Terminal**

- **kitty** with the `charcoal.conf` theme, using its own tabs and splits.
  Super+A toggles a floating scratch terminal.
- **zsh** with starship, lazy nvm, cached completions; **bat**, **lazygit**,
  **fastfetch**, **cava** on the same palette.
- **Neovim** (lazy.nvim, LSP, DAP, treesitter).

**Browser**

- **Zen** styling, privacy prefs and add-on policies applied by
  `zen-style/apply.py` into whichever profile exists. No profile data is
  tracked (`zen-style/README.md`).

## Install

```bash
chezmoi init --apply D4NZ-jpg
```

`run_after_install_pkgs.sh` runs `setup/scripts/install.sh`: packages from
`setup/pkgs/pkgs.lst` (and `extras.lst`), the NVIDIA driver chosen for the
detected GPU (`nvidia.sh`), services from `system_ctl.lst`, then
`post-install.sh` (default shell, Zen, icons, Hyprland plugins). Arch only.

Zellij (and tmux before it) has been removed; remote agent work moved to
t3code. Applying these files does not stop running sessions or uninstall
packages.

New tools go in `setup/pkgs/pkgs.lst`; per-machine paths use chezmoi
templates (`qt6ct.conf.tmpl`), never absolute home paths.

## Tests

`tests/` holds Python and QML checks for the installer helpers, the Zen
scripts, the Quickshell popups, the screenshot backend and the Neovim DAP
config. They run without touching the live system:

```bash
python tests/installer-utils.py
python tests/quickshell-panel.py
python tests/screenshot-capture.py
```
