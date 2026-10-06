"""aem doctor: is AEM installed and able to record here? Read-only; it changes nothing.

Checks, each ok, warn or fail:

  aem          this command's version and the Python running it
  ffmpeg       ffmpeg and ffprobe on PATH (render checks need both)
  registry     the registry loads; each client's design system and projects root can be read (a drive mounted)
  project      the project resolved from here, and its frame rate
  plugin       the Claude Code plugin installed for this user has the same version as this command
               (its record: ~/.claude/plugins/installed_plugins.json; AEM_CLAUDE_DIR names another ~/.claude)
  nonces       the folder the plugin's slash commands write their one-time nonces to can be written
  integrity    ledger lines AEM did not write, for the resolved project
  drift        the client's text exports and installed skill against their masters

Exit 1 when a check fails; warnings do not fail it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import VERSION, drift, integrity, registry
from .util import AemError, aem_home, expand

PLUGIN = "aavkar-educational-motion-studio"


def _check(name: str, status: str, detail: str) -> dict:
    return {"check": name, "status": status, "detail": detail}


def _tool_version(tool: str) -> str | None:
    path = shutil.which(tool)
    if not path:
        return None
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10).stdout
        return (out.splitlines() or [path])[0]
    except (OSError, subprocess.SubprocessError):
        return path


def installed_plugin_versions(claude_dir: Path) -> list[str]:
    try:
        data = json.loads((claude_dir / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    plugins = data.get("plugins", data) if isinstance(data, dict) else {}
    out = []
    for key, entries in plugins.items():
        if key.split("@")[0] == PLUGIN:
            for e in entries if isinstance(entries, list) else [entries]:
                if isinstance(e, dict) and e.get("version"):
                    out.append(str(e["version"]))
    return out


def doctor(args, *, claude_dir: Path | None = None) -> dict:
    checks = [_check("aem", "ok", f"aem {VERSION}, Python {sys.version.split()[0]} at {sys.executable}")]
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    checks.append(_check("ffmpeg", "fail" if missing else "ok",
                         f"not on PATH: {', '.join(missing)} (render checks need them)" if missing
                         else _tool_version("ffprobe") or "ffprobe found"))
    reg_path = registry.registry_path(getattr(args, "registry", None))
    try:
        reg = registry.load_registry(reg_path)
        unreadable = [f"{c['id']}: {p}" for c in reg["clients"] for p in (c["design_system"], c["projects_root"])
                      if not expand(p).is_dir()]
        checks.append(_check("registry", "warn" if unreadable else "ok",
                             f"{reg_path}, {len(reg['clients'])} client(s)"
                             + (f"; cannot read {'; '.join(unreadable)} (is the drive mounted?)" if unreadable else "")))
    except AemError as exc:
        checks.append(_check("registry", "fail", exc.message))
        reg = None
    ctx = None
    if reg is not None:
        try:
            ctx = registry.context(args, require_project=False)
            if ctx.project:
                fps = f"{ctx.fps.numerator}/{ctx.fps.denominator} from {ctx.fps_source}" if ctx.fps else "no frame rate stated"
                checks.append(_check("project", "ok" if ctx.fps else "warn",
                                     f"{ctx.client.id}/{ctx.project} ({ctx.resolution.source}), {fps}"))
            else:
                checks.append(_check("project", "ok", f"client {ctx.client.id}, no project ({ctx.resolution.source})"))
        except registry.NoProject:
            checks.append(_check("project", "ok", "none resolved here: AEM records nothing in this folder"))
        except AemError as exc:
            checks.append(_check("project", "fail", exc.message))
    versions = installed_plugin_versions(claude_dir or expand(os.environ.get("AEM_CLAUDE_DIR") or "~/.claude"))
    if not versions:
        checks.append(_check("plugin", "warn", f"{PLUGIN} is not installed for this user (or was installed elsewhere)"))
    elif VERSION in versions:
        checks.append(_check("plugin", "ok", f"{PLUGIN} {VERSION} installed; start a new session after an update"))
    else:
        checks.append(_check("plugin", "fail", f"{PLUGIN} {', '.join(versions)} installed, this command is {VERSION}: "
                                               "update the plugin (INSTALL.md, Updating), then start a new session"))
    nonces = aem_home() / "nonces"
    probe = nonces if nonces.exists() else aem_home() if aem_home().exists() else aem_home().parent
    checks.append(_check("nonces", "ok" if os.access(probe, os.W_OK) else "fail",
                         f"{nonces} {'can' if os.access(probe, os.W_OK) else 'cannot'} be written (slash commands need it)"))
    if ctx is not None and ctx.project:
        integ = integrity.check(ctx)
        changed = [f["name"] for f in integ["files"] if f["findings"]]
        waiting = f"; no baseline yet for {', '.join(integ['no_baseline'])} (made on AEM's first write)" if integ["no_baseline"] else ""
        checks.append(_check("integrity", "warn" if integ["findings"] else "ok",
                             (f"{integ['findings']} ledger edit(s) to review in {', '.join(changed)}: aem integrity"
                              if integ["findings"] else "the ledgers match what AEM wrote") + waiting))
    if ctx is not None:
        d = drift.drift(ctx.client, expand("~/.claude/skills"))
        checks.append(_check("drift", "warn" if d["findings"] else "ok",
                             f"{len(d['findings'])} finding(s): aem drift" if d["findings"] else "no drift"))
    failed = [c for c in checks if c["status"] == "fail"]
    return {"ok": not failed, "checks": checks, "failed": len(failed),
            "warnings": len([c for c in checks if c["status"] == "warn"])}


def text(r: dict) -> str:
    mark = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}
    return "\n".join(f"{mark[c['status']]} {c['check']}: {c['detail']}" for c in r["checks"])
