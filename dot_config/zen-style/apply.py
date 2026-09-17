#!/usr/bin/env python3
"""Apply browser styling and privacy defaults locally; never collect profile data."""
import configparser
import os
from pathlib import Path
import re

IMPORT = '@import url("chezmoi-theme.css");'
PREFS = {
    "toolkit.legacyUserProfileCustomizations.stylesheets": "true",
    "zen.view.window.scheme": "0",
    # Strict ETP; leave its evolving feature set to the browser.
    "browser.contentblocking.category": '"strict"',
    "privacy.trackingprotection.enabled": "true",
    "privacy.trackingprotection.pbmode.enabled": "true",
    "dom.security.https_only_mode": "true",
    "dom.security.https_only_mode_pbm": "true",
    # Do not send partially typed searches to the search provider.
    "browser.search.suggest.enabled": "false",
    "browser.urlbar.suggest.searches": "false",
    "browser.urlbar.quicksuggest.enabled": "false",
    # Block new notification requests; existing site grants are left intact.
    "permissions.default.desktop-notification": "2",
    # Camera, microphone and location continue to require site permission.
    "permissions.default.camera": "0",
    "permissions.default.microphone": "0",
    "permissions.default.geo": "0",
    # Bitwarden handles passwords. Do not delete existing saved information.
    "signon.rememberSignons": "false",
    "signon.autofillForms": "false",
    "extensions.formautofill.addresses.enabled": "false",
    "extensions.formautofill.creditCards.enabled": "false",
    # Keep browser security checks enabled.
    "browser.safebrowsing.malware.enabled": "true",
    "browser.safebrowsing.phishing.enabled": "true",
    "browser.safebrowsing.downloads.enabled": "true",
    "xpinstall.signatures.required": "true",
}


def write_if_changed(path, text):
    if path.is_symlink():
        raise ValueError("Refusing to overwrite a symlink")
    if path.exists() and path.read_text() == text:
        return
    # Exclusive creation keeps newly created preference files private.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(text)


def apply_profile(profile, theme):
    chrome = profile / "chrome"
    targets = [chrome, chrome / "userChrome.css", chrome / "chezmoi-theme.css", profile / "user.js"]
    if any(p.is_symlink() for p in targets):
        raise ValueError("Refusing symlinked theme/preference targets")
    chrome.mkdir(exist_ok=True, mode=0o700)
    css_path = chrome / "userChrome.css"
    css = css_path.read_text() if css_path.exists() else ""
    # Migrate our original standalone theme without duplicating its rules.
    if css == theme:
        css = ""
    if IMPORT not in css.splitlines():
        # CSS @import must precede ordinary rules (but follow @charset).
        charset = re.match(r'^\s*@charset\s+[^;]+;\s*', css)
        pos = charset.end() if charset else 0
        css = css[:pos] + IMPORT + "\n" + css[pos:]
    pref_path = profile / "user.js"
    prefs = pref_path.read_text() if pref_path.exists() else ""
    for key, value in PREFS.items():
        line = f'user_pref("{key}", {value});'
        pattern = r'^\s*user_pref\(\s*[\"\x27]' + re.escape(key) + r'[\"\x27]\s*,[^\n]*\);[^\n]*$'
        prefs, count = re.subn(pattern, lambda _: line, prefs, flags=re.MULTILINE)
        if not count:
            prefs = prefs.rstrip("\n") + ("\n" if prefs else "") + line + "\n"
    write_if_changed(chrome / "chezmoi-theme.css", theme)
    write_if_changed(css_path, css)
    write_if_changed(pref_path, prefs)


def apply(root, theme):
    ini = root / "profiles.ini"
    if not ini.is_file():
        return 0
    config = configparser.ConfigParser(interpolation=None)
    config.read(ini)
    profiles = set()
    for section in config.sections():
        if not section.startswith("Profile") or not config.has_option(section, "Path"):
            continue
        path = Path(config[section]["Path"])
        if config[section].get("IsRelative", "1") == "1":
            path = root / path
        # Only touch profiles inside the local Zen directory, never arbitrary paths.
        resolved = path.resolve()
        if resolved == root.resolve() or not resolved.is_relative_to(root.resolve()):
            continue
        if path.is_symlink() or not path.is_dir():
            continue
        profiles.add(resolved)
    for profile in sorted(profiles):
        apply_profile(profile, theme)
    return len(profiles)


def main():
    theme = Path(__file__).with_name("theme.css").read_text()
    count = apply(Path.home() / ".zen", theme)
    print(f"Zen styling and privacy defaults applied to {count} local profile(s). Restart Zen to load changes.")


if __name__ == "__main__":
    main()
