#!/usr/bin/env python3
"""Keeps tests and test scripts off the operator's real AEM state.

The real state is the operator's ~/.aem (the active project) and this repository's
registry/clients.json. Tests run against a sandbox instead: a fresh temp AEM_HOME and a temp copy
of the registry whose clients' folders are moved inside the sandbox, so nothing run against it
can reach a real client folder either.

From Python (tests/helpers.py imports it):  snapshot(), changed(before, after), sandbox(prefix).

From a shell script:
    python3 tests/isolation.py snapshot FILE        write the real state's snapshot to FILE
    python3 tests/isolation.py check FILE           exit 1, listing what changed since FILE
    python3 tests/isolation.py sandbox [PREFIX]     make a sandbox; print `export` lines for it
    python3 tests/isolation.py verify DIR           exit 2 unless DIR is a sandbox that is safe to use
"""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REAL_REGISTRY = REPO / "registry" / "clients.json"
# The account's own home, not $HOME: a test may point HOME somewhere else.
REAL_AEM_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".aem"
MARKER = ".aem-test-sandbox"


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot() -> dict[str, str | None]:
    """Every file under the real ~/.aem and the real registry, by content hash (None: missing)."""
    snap: dict[str, str | None] = {"registry/clients.json": _digest(REAL_REGISTRY) if REAL_REGISTRY.is_file() else None}
    if REAL_AEM_HOME.is_dir():
        for p in sorted(REAL_AEM_HOME.rglob("*")):
            key = "~/.aem/" + str(p.relative_to(REAL_AEM_HOME))
            snap[key] = "<dir>" if p.is_dir() else _digest(p) if p.is_file() else "<other>"
    else:
        snap["~/.aem"] = None
    return snap


def changed(before: dict, after: dict) -> list[str]:
    out = []
    for k in sorted(set(before) | set(after)):
        if before.get(k, "<absent>") != after.get(k, "<absent>"):
            what = "added" if k not in before else "removed" if k not in after else "changed"
            out.append(f"{k} {what}")
    return out


@dataclass
class Sandbox:
    root: Path

    @property
    def home(self) -> Path:
        return self.root / "aem-home"

    @property
    def registry(self) -> Path:
        return self.root / "clients.json"

    @property
    def env(self) -> dict[str, str]:
        # AEM_SANDBOX=1 lets aem resolve projects in temporary folders; it is set only here.
        return {"AEM_HOME": str(self.home), "AEM_REGISTRY": str(self.registry), "AEM_SANDBOX": "1",
                "AEM_SANDBOX_DIR": str(self.root)}

    def register_project(self, client_id: str, name: str, rel_dir: str) -> Path:
        """Register a project folder (relative to the client's projects_root) in the sandbox registry."""
        reg = json.loads(self.registry.read_text(encoding="utf-8"))
        for c in reg["clients"]:
            if c["id"] == client_id:
                c.setdefault("projects", {})[name] = {"dir": rel_dir}
                self.registry.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
                return Path(c["projects_root"]) / rel_dir
        raise KeyError(client_id)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def sandbox(prefix: str = "aem-sandbox-") -> Sandbox:
    """A fresh AEM_HOME and a temp copy of the registry, every client's folders moved inside it.

    A client's projects_root becomes <sandbox>/<its folder name> and its design system
    <that>/<its folder name>. Its registered projects stay (their folders are relative to the
    projects root); register_project() adds a test copy. Nothing else in the entry changes.
    """
    sb = Sandbox(Path(tempfile.mkdtemp(prefix=prefix)).resolve())
    sb.home.mkdir()
    (sb.root / MARKER).write_text("AEM test sandbox: safe to delete.\n", encoding="utf-8")
    reg = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    for c in reg.get("clients", []):
        root = sb.root / Path(c["projects_root"]).name
        c["projects_root"] = str(root)
        c["design_system"] = str(root / Path(c["design_system"]).name)
    reg["_comment"] = "AEM test sandbox: a copy of registry/clients.json with every client's folders inside this sandbox."
    sb.registry.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    return sb


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def problems(root: Path) -> list[str]:
    """Why `root` is not safe to run against (empty: it is)."""
    sb = Sandbox(root)
    if not (root / MARKER).is_file():
        return [f"{root} is not a test sandbox (no {MARKER}; make one with: tests/isolation.py sandbox)"]
    out = []
    if _inside(sb.home, REAL_AEM_HOME) or sb.home.resolve() == REAL_AEM_HOME.resolve():
        out.append(f"AEM_HOME {sb.home} is the real ~/.aem")
    if sb.registry.resolve() == REAL_REGISTRY.resolve():
        out.append(f"registry {sb.registry} is the real registry")
    try:
        reg = json.loads(sb.registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return out + [f"registry {sb.registry} unreadable: {e}"]
    for c in reg.get("clients", []):
        for key in ("design_system", "projects_root"):
            if not _inside(Path(os.path.expanduser(c.get(key, ""))), root):
                out.append(f"client {c.get('id')!r} {key} {c.get(key)!r} is outside the sandbox")
    return out


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "snapshot" and len(argv) == 2:
        Path(argv[1]).write_text(json.dumps(snapshot(), indent=1), encoding="utf-8")
        return 0
    if cmd == "check" and len(argv) == 2:
        diff = changed(json.loads(Path(argv[1]).read_text(encoding="utf-8")), snapshot())
        for d in diff:
            print(f"ISOLATION FAILED: {d}", file=sys.stderr)
        if not diff:
            print("isolation: ~/.aem and registry/clients.json unchanged")
        return 1 if diff else 0
    if cmd == "sandbox" and len(argv) <= 2:
        sb = sandbox(argv[1] if len(argv) == 2 else "aem-sandbox-")
        for k, v in sb.env.items():
            print(f"export {k}={_sh(v)}")
        return 0
    if cmd == "verify" and len(argv) == 2:
        bad = problems(Path(argv[1]))
        for b in bad:
            print(f"refusing: {b}", file=sys.stderr)
        return 2 if bad else 0
    print(__doc__, file=sys.stderr)
    return 2


def _sh(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
