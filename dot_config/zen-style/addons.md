# Zen addons

The public policies in `addon-policies.json` automatically install:

- [Bitwarden](https://addons.mozilla.org/firefox/addon/bitwarden-password-manager/)
- [uBlock Origin](https://addons.mozilla.org/firefox/addon/ublock-origin/)
- [SponsorBlock](https://addons.mozilla.org/firefox/addon/sponsorblock/)

For Arch's `zen-browser-bin`, install the policies with:

```sh
sudo python3 "$HOME/.config/zen-style/install-addons.py"
```

This merges the rules into `/opt/zen-browser-bin/distribution/policies.json`, preserves unrelated policies, and keeps a private pre-change backup next to that file. The policy applies to all profiles using this Zen installation. `normal_installed` allows addons to be disabled or removed; it does not force-lock them.

Restart Zen, then check `about:policies` for active rules/errors and `about:addons` for the installed extensions. Network access is required for installation. These are Mozilla's latest signed releases, not pinned versions.

The policy file belongs to the Zen package, so updates may replace it. Re-run the idempotent command after an update if the addon policies disappear. The chezmoi styling hook does not run sudo or install these policies itself.

Use Zen's built-in container support; no separate Containers extension is included. Sign into Bitwarden normally. Never copy vaults, extension storage, account tokens, or browser profile data into the repository.
