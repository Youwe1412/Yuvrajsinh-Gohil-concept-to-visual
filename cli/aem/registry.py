"""The client registry, the active project and the context every command works in.

Nothing client-specific lives in code: names, paths, protected files, blocked commands,
gates and idle time all come from registry/clients.json.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from . import fps as fpsmod
from .util import AemError, REPO_ROOT, aem_home, expand, read_json, ts, write_json_atomic

DEFAULT_GATES = {
    "G1": "Inputs", "G2": "Plan", "G3": "Stills", "G4": "Rough render",
    "G5": "Critique and repair", "G6": "Deliver", "G7": "Client review",
}


def registry_path(explicit: str | None = None) -> Path:
    if explicit:
        return expand(explicit).resolve()
    if os.environ.get("AEM_REGISTRY"):
        return expand(os.environ["AEM_REGISTRY"]).resolve()
    return REPO_ROOT / "registry" / "clients.json"


def load_registry(path: Path) -> dict:
    data = read_json(path)
    if data is None:
        raise AemError(f"registry not found: {path}")
    clients = data.get("clients")
    if not isinstance(clients, list):
        raise AemError(f"{path}: 'clients' must be a list")
    seen = set()
    for c in clients:
        for key in ("id", "name", "design_system", "projects_root", "decisions_file", "rules_file"):
            if not c.get(key):
                raise AemError(f"{path}: client {c.get('id', '?')!r} is missing {key!r}")
        if c["id"] in seen:
            raise AemError(f"{path}: duplicate client id {c['id']!r}")
        seen.add(c["id"])
    return data


@dataclass
class Client:
    raw: dict
    registry: dict

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def contact(self) -> str:
        return self.raw.get("contact") or self.raw["id"]

    @property
    def design_system(self) -> Path:
        return expand(self.raw["design_system"])

    @property
    def projects_root(self) -> Path:
        return expand(self.raw["projects_root"])

    @property
    def decisions_path(self) -> Path:
        return self.design_system / self.raw["decisions_file"]

    @property
    def rules_path(self) -> Path:
        return self.design_system / self.raw["rules_file"]

    @property
    def labelled_cases_path(self) -> Path:
        return self.design_system / self.raw.get("labelled_cases_file", "critic/labelled-cases.jsonl")

    @property
    def decisions_order(self) -> str:
        return self.raw.get("decisions_order", "newest_first")

    @property
    def skill(self) -> str | None:
        return self.raw.get("skill")

    @property
    def skill_master(self) -> Path | None:
        rel = self.raw.get("skill_master")
        return (self.design_system / rel) if rel else None

    @property
    def gates(self) -> dict:
        return self.raw.get("gates") or DEFAULT_GATES

    @property
    def idle_minutes(self) -> float:
        return float(self.raw.get("idle_minutes", 10))

    @property
    def protected(self) -> dict:
        p = self.raw.get("protected_files") or {}
        return {"design_system": list(p.get("design_system", [])), "project": list(p.get("project", []))}

    @property
    def blocked_commands(self) -> list:
        return list(self.raw.get("blocked_commands", []))

    @property
    def waiting_ids(self) -> set:
        """Names that count as 'waiting on the client' in the time report."""
        ids = {self.id.lower()}
        ids.update(x.lower() for x in self.raw.get("waiting_on_client_ids", []))
        return ids

    @property
    def operator(self) -> str:
        return (self.registry.get("operator") or {}).get("name", "operator")

    @property
    def operator_id(self) -> str:
        return (self.registry.get("operator") or {}).get("id", self.operator.lower())

    def project_entries(self) -> dict:
        return self.raw.get("projects") or {}


def find_client(registry: dict, client_id: str) -> Client:
    for c in registry["clients"]:
        if c["id"] == client_id:
            return Client(c, registry)
    known = ", ".join(c["id"] for c in registry["clients"]) or "none"
    raise AemError(f"unknown client {client_id!r} (registered: {known})", hint="Add one with: aem new-client <id>")


def resolve_project(client: Client, name: str, path: str | None = None) -> tuple[str, Path]:
    """A project folder by explicit path, registry entry, exact folder name or unique 'NAME - ' prefix."""
    if path:
        p = expand(path).resolve()
        if not p.is_dir():
            raise AemError(f"project folder not found: {p}")
        return name, p
    entry = client.project_entries().get(name)
    if entry:
        p = (client.projects_root / entry["dir"]).resolve()
        if not p.is_dir():
            raise AemError(f"registry project {name!r} points at a missing folder: {p}")
        return name, p
    root = client.projects_root
    if not root.is_dir():
        raise AemError(f"projects_root for {client.id!r} is not readable: {root}",
                       hint="Is the drive mounted?")
    exact = root / name
    if exact.is_dir():
        return name, exact.resolve()
    matches = [d for d in root.iterdir()
               if d.is_dir() and (d.name.startswith(name + " - ") or d.name.startswith(name + " "))]
    if len(matches) == 1:
        return matches[0].name, matches[0].resolve()
    if len(matches) > 1:
        raise AemError(f"{name!r} matches several projects: " + ", ".join(sorted(m.name for m in matches)))
    raise AemError(f"no project {name!r} under {root}",
                   hint="Use the folder name, a 'P1'-style prefix, or --path for a folder elsewhere.")


def active_path() -> Path:
    return aem_home() / "active.json"


def read_active() -> dict | None:
    return read_json(active_path())


def write_active(data: dict) -> None:
    write_json_atomic(active_path(), data)


@dataclass
class Context:
    registry_path: Path
    registry: dict
    client: Client
    project: str | None = None
    project_dir: Path | None = None
    fps: Fraction | None = None
    fps_source: str | None = None
    active: dict = field(default_factory=dict)

    @property
    def events_path(self) -> Path:
        return self.project_dir / "events.jsonl"

    @property
    def approvals_path(self) -> Path:
        return self.project_dir / "approvals.jsonl"

    def project_settings(self) -> dict:
        return read_json(self.project_dir / fpsmod.PROJECT_SETTINGS, {}) or {}

    def summary(self) -> dict:
        return {
            "client": self.client.id,
            "client_name": self.client.name,
            "project": self.project,
            "project_dir": str(self.project_dir) if self.project_dir else None,
            "design_system": str(self.client.design_system),
            "fps": fpsmod.rate_dict(self.fps, self.fps_source) if self.fps else None,
            "registry": str(self.registry_path),
        }


def context(args, *, require_project: bool = True) -> Context:
    """The client and project a command acts on: --client/--project if given, else the active one."""
    client_id = getattr(args, "client", None)
    project = getattr(args, "project", None)
    reg_arg = getattr(args, "registry", None)
    active = read_active() or {}
    if client_id or project:
        if not client_id:
            client_id = active.get("client")
            if not client_id:
                raise AemError("--project needs --client when no project is active")
        rpath = registry_path(reg_arg or (active.get("registry") if active.get("client") == client_id else None))
        reg = load_registry(rpath)
        client = find_client(reg, client_id)
        if not project:
            if require_project:
                raise AemError("--client given without --project")
            return Context(rpath, reg, client)
        if active.get("client") == client_id and active.get("project") == project:
            pdir = Path(active["project_dir"])
        else:
            project, pdir = resolve_project(client, project)
        try:
            fps = fpsmod.resolve(pdir)
            rate, source = fps["fps"], fps["source"]
        except AemError:
            rate, source = None, None
        if active.get("project_dir") == str(pdir) and active.get("fps"):
            rate, source = fpsmod.parse_rate(active["fps"]), active["fps"].get("source")
        return Context(rpath, reg, client, project, pdir, rate, source, active)
    if not active.get("client"):
        raise AemError("no active project", hint="Run: aem use <client>/<project>")
    rpath = registry_path(reg_arg or active.get("registry"))
    reg = load_registry(rpath)
    client = find_client(reg, active["client"])
    pdir = Path(active["project_dir"]) if active.get("project_dir") else None
    if require_project and (pdir is None or not pdir.is_dir()):
        raise AemError(f"active project folder is not readable: {pdir}", hint="Is the drive mounted? Or run aem use again.")
    rate = fpsmod.parse_rate(active["fps"]) if active.get("fps") else None
    return Context(rpath, reg, client, active.get("project"), pdir, rate,
                   (active.get("fps") or {}).get("source"), active)


def use(spec: str, *, path: str | None = None, fps_override: str | None = None,
        registry: str | None = None) -> dict:
    if "/" not in spec:
        raise AemError("use takes <client>/<project>", hint="For example: aem use joel/P2")
    client_id, project = spec.split("/", 1)
    rpath = registry_path(registry)
    reg = load_registry(rpath)
    client = find_client(reg, client_id)
    project, pdir = resolve_project(client, project, path)
    rate = fpsmod.resolve(pdir, fps_override)
    data = {
        "client": client.id,
        "project": project,
        "project_dir": str(pdir),
        "registry": str(rpath),
        "fps": fpsmod.rate_dict(rate["fps"], rate["source"]),
        "set_at": ts(),
    }
    write_active(data)
    data["fps_candidates"] = rate["candidates"]
    return data
