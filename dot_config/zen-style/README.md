# Zen browser styling

`theme.css` styles browser chrome only. Websites are not restyled.

`apply.py` reads `~/.zen/profiles.ini` locally and applies the theme to existing profiles inside `~/.zen`. It copies `theme.css` to `chrome/chezmoi-theme.css`, adds a relative import to `userChrome.css`, and sets two `user.js` preferences: custom stylesheet support and Zen's dark window scheme. Existing custom rules and unrelated preferences are retained. Existing rules may override the imported theme.

The chezmoi after-hook runs this on apply. On a fresh installation, launch and close Zen once to create a profile, then run:

```sh
python3 ~/.config/zen-style/apply.py
```

Restart Zen after changes. Profiles stored outside `~/.zen` and Flatpak profiles are intentionally not modified. Python 3 is required and declared in the package list.

Do not add browser profiles to chezmoi. `.zen` is ignored: cookies, passwords, history, bookmarks, sessions, extensions, and profile registries are not part of this configuration. The installer prints only the number of profiles updated.

To stop using the theme, remove the `chezmoi-theme.css` import from each profile's `chrome/userChrome.css`; other custom rules will remain. The two preferences can be changed locally after disabling the apply hook.
