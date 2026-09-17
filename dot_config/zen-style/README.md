# Zen browser styling

`theme.css` styles browser chrome only. Websites are not restyled.

`apply.py` reads `~/.zen/profiles.ini` locally and applies the theme to existing profiles inside `~/.zen`. It copies `theme.css` to `chrome/chezmoi-theme.css`, adds a relative import to `userChrome.css`, and sets the styling and balanced privacy preferences listed in `PREFS`. Existing custom rules and unrelated preferences are retained. Existing rules may override the imported theme.

The main post-install script runs `~/setup/scripts/zen-setup.sh`: it initializes a default profile headlessly if needed, applies styling/privacy preferences, installs addon policies with sudo, and sets Zen as the default browser. It does not copy profile data or sign into accounts.

The separate chezmoi theme hook also refreshes existing profiles on apply without sudo. If using the theme independently of the full installer, launch and close Zen once to create a profile, then run:

```sh
python3 ~/.config/zen-style/apply.py
```

Restart Zen after changes. Profiles stored outside `~/.zen` and Flatpak profiles are intentionally not modified. Python 3 is required and declared in the package list.

Do not add browser profiles to chezmoi. `.zen` is ignored: cookies, passwords, history, bookmarks, sessions, extensions, and profile registries are not part of this configuration. The installer prints only the number of profiles updated.

To stop using the theme, remove the `chezmoi-theme.css` import from each profile's `chrome/userChrome.css`; other custom rules will remain. Managed preferences are reapplied on browser startup through `user.js`. To undo them, disable the apply hook, remove the relevant lines from local `user.js`, then reset those preferences in `about:config` (removing the lines alone does not reset saved values).

## Balanced privacy defaults

- Strict tracking protection and HTTPS-Only mode, including private windows.
- No remote search suggestions or Quick Suggest.
- New website notification requests blocked; existing site grants remain unchanged.
- Camera, microphone and location remain permission-based.
- Browser password saving/autofill and address/payment autofill disabled; existing saved data is not deleted.
- Safe Browsing phishing, malware and download checks, and extension-signature enforcement enabled.

DNS, cookies-on-exit, fingerprinting resistance, extension storage and uBlock lists are not changed. Strict tracking protection or HTTPS-Only may require exceptions for individual sites.

In Bitwarden, set vault timeout to a short interval with the action **Lock**, and enable account MFA (prefer a passkey/security key or authenticator). Keep recovery codes offline. These account/vault settings are deliberately not managed by dotfiles.

Keep Zen updated using the Arch package manager; the package disables its own internal updater. This installer does not alter that policy.
