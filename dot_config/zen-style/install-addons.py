#!/usr/bin/env python3
"""Merge public addon policies into the Arch zen-browser-bin installation."""
import json
import os
from pathlib import Path
import tempfile

TARGET = Path("/opt/zen-browser-bin/distribution/policies.json")


def merge(existing, desired):
    # Work on a copy; preserve unrelated policies and per-extension settings.
    result = json.loads(json.dumps(existing))
    settings = result.setdefault("policies", {}).setdefault("ExtensionSettings", {})
    for extension, rules in desired["policies"]["ExtensionSettings"].items():
        settings.setdefault(extension, {}).update(rules)
    return result


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo: python3 ~/.config/zen-style/install-addons.py")
    if not TARGET.parent.is_dir():
        raise SystemExit("Arch zen-browser-bin installation not found; no changes made.")
    if TARGET.is_symlink():
        raise SystemExit("Refusing to replace a symlinked policy file.")
    desired = json.loads(Path(__file__).with_name("addon-policies.json").read_text())
    original = TARGET.read_text() if TARGET.exists() else "{}"
    merged = merge(json.loads(original), desired)
    if merged == json.loads(original):
        print("Zen addon policies are already installed.")
        return
    # Keep the pre-change package policy outside the dotfiles repository.
    if TARGET.exists():
        fd, backup = tempfile.mkstemp(prefix="policies.before-zen-addons-", suffix=".json", dir=TARGET.parent)
        with os.fdopen(fd, "w") as stream:
            stream.write(original)
    fd, temporary = tempfile.mkstemp(prefix=".policies-", dir=TARGET.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(merged, stream, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o644)
        os.replace(temporary, TARGET)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("Installed Zen addon policies. Restart Zen and check about:policies and about:addons.")


if __name__ == "__main__":
    main()
