#!/usr/bin/env python3
"""Collect sync state for the panel into one JSON file.

Sources, all local and fast (no network):
  handoff   ~/.local/state/projects/handoff-status.json written by `projects handoff`
  incoming  WIP refs other machines pushed, as already fetched into each repo
            by `projects incoming` (refs/wip/<machine>/<worktree>)
  syncthing local REST API: per-folder state, pending items, errors

Output: ~/.local/state/projects/panel-status.json
  {"level": "idle|busy|attention|error", "handoff": {...}, "incoming": [...],
   "syncthing": {"folders": [...], "syncing": n, "errors": n, "paused": n}}
"""
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

STATE = Path(os.path.expanduser("~/.local/state/projects"))
OUT = STATE / "panel-status.json"
CATALOG = Path(os.path.expanduser("~/.config/projects/catalog.json"))
ME = os.uname().nodename.split(".")[0]


def handoff():
    try:
        d = json.loads((STATE / "handoff-status.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {"state": "unknown"}
    return {k: d.get(k) for k in ("state", "dirty", "last_ok", "last_error", "updated", "trigger")}


def repo_dirs():
    """Project name -> local repo path, from the projects catalog."""
    try:
        cat = json.loads(CATALOG.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    dev = Path(os.path.expanduser("~/dev"))
    out = {}
    items = cat.get("projects", cat) if isinstance(cat, dict) else {}
    for name, p in items.items():
        rel = p.get("path") if isinstance(p, dict) else None
        if rel and (dev / rel / ".git").exists():
            out[name] = dev / rel
    return out


def incoming():
    """WIP refs from other machines, read from local refs (no fetch)."""
    rows = []
    for name, repo in repo_dirs().items():
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "for-each-ref", "--format=%(refname)\t%(committerdate:unix)\t%(subject)", "refs/wip"],
                capture_output=True, text=True, timeout=10,
            ).stdout
        except (subprocess.TimeoutExpired, OSError):
            continue
        for line in out.splitlines():
            ref, when, subject = line.split("\t", 2)
            _, _, machine, wt = ref.split("/", 3)
            if machine == ME:
                continue
            rows.append({"project": name, "worktree": wt, "from": machine, "when": int(when)})
    rows.sort(key=lambda r: -r["when"])
    return rows


def syncthing():
    try:
        cfg = Path(os.path.expanduser("~/.local/state/syncthing/config.xml")).read_text()
        key = re.search(r"<apikey>([^<]+)</apikey>", cfg).group(1)
    except (OSError, AttributeError):
        return {"folders": [], "syncing": 0, "errors": 0, "paused": 0, "available": False}
    h = {"X-API-Key": key}

    def get(path):
        return json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8384/rest" + path, headers=h), timeout=5))

    try:
        folders = get("/config/folders")
    except Exception:
        return {"folders": [], "syncing": 0, "errors": 0, "paused": 0, "available": False}
    rows, syncing, errors, paused = [], 0, 0, 0
    for f in folders:
        label = f.get("label") or f["id"]
        if f.get("paused"):
            paused += 1
            rows.append({"label": label, "state": "paused", "need": 0, "errors": 0})
            continue
        try:
            s = get("/db/status?folder=" + f["id"])
        except Exception:
            rows.append({"label": label, "state": "unknown", "need": 0, "errors": 0})
            continue
        state, need, errs = s.get("state", ""), int(s.get("needTotalItems", 0)), int(s.get("errors", 0))
        if errs or state == "error":
            errors += 1
        elif state not in ("idle", "") or need:
            syncing += 1
        rows.append({"label": label, "state": state or "idle", "need": need, "errors": errs})
    rows.sort(key=lambda r: (r["state"] == "paused", -r["errors"], -r["need"], r["label"].lower()))
    return {"folders": rows, "syncing": syncing, "errors": errors, "paused": paused, "available": True}


def main():
    h, inc, st = handoff(), incoming(), syncthing()
    if h.get("state") == "error" or st["errors"]:
        level = "error"
    elif inc or h.get("state") == "skipped":
        level = "attention"
    elif st["syncing"]:
        level = "busy"
    else:
        level = "idle"
    doc = {"level": level, "handoff": h, "incoming": inc, "syncthing": st, "machine": ME, "updated": int(time.time())}
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc))
    os.replace(tmp, OUT)


if __name__ == "__main__":
    main()
