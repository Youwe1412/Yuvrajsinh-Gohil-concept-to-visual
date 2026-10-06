"""The client registry, the project a command resolves, and the context every command works in.

Nothing client-specific lives in code: names, paths, gates, approval and delivery patterns, render
scripts, review settings and idle time all come from registry/clients.json. (Since 1.0.0 nothing reads
an entry's protected_files, blocked_commands, shared_paths or audio_libraries: they belonged to the guard.)
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


# --- the last-used hint -----------------------------------------------------------------
#
# ~/.aem/active.json is no longer state anything trusts. `aem use` still writes it so that a bare
# Terminal can say what was used last, and only `aem status` reads it, labelled as a hint. The
# project a command acts on is resolved from AEM_PROJECT, the plugin's session pin or the working
# folder (see resolve()), never from this file.

HINT_NOTE = ("Last-used hint only. `aem status` shows it in a bare terminal; nothing else reads it. "
             "A command's project comes from AEM_PROJECT, the session pin or the working folder.")


def hint_path() -> Path:
    return aem_home() / "active.json"


def write_hint(client: str, project: str, project_dir: Path) -> None:
    write_json_atomic(hint_path(), {"_comment": HINT_NOTE, "client": client, "project": project,
                                    "project_dir": str(project_dir), "set_at": ts()})


def clear_hint() -> dict | None:
    """Forget the last-used hint. Returns what it said."""
    was = read_json(hint_path()) if hint_path().exists() else None
    if hint_path().exists():
        hint_path().unlink()
    return was


def read_hint(reg: dict | None = None) -> tuple[dict | None, str | None]:
    """(hint, note). A hint that points outside the registry's real roots is renamed to
    active.json.stale and the note says so: the acceptance run left one pointing at /tmp."""
    p = hint_path()
    if not p.exists():
        return None, None
    try:
        data = read_json(p) or {}
    except (OSError, ValueError):
        data = {}
    problem = None
    where = data.get("project_dir")
    if not where:
        problem = "it names no project folder"
    elif reg is not None:
        problem = folder_problem(reg, data.get("client"), Path(where))
    if problem:
        stale = p.with_name(p.name + ".stale")
        os.replace(p, stale)
        return None, f"moved {p} to {stale.name}: it pointed at {where or 'nothing'}, which was refused ({problem})"
    return data, None


# --- where a project may live -----------------------------------------------------------

TMP_ROOTS = ("/tmp", "/private/tmp")


def sandbox_allowed() -> bool:
    """AEM_SANDBOX=1: tests and acceptance runs, whose folders are temporary by design."""
    return os.environ.get("AEM_SANDBOX") == "1"


def _real(p) -> Path:
    return Path(os.path.realpath(expand(p)))


def _inside(p: Path, root: Path) -> bool:
    return p == root or root in p.parents


def folder_problem(reg: dict, client_id: str | None, pdir: Path) -> str | None:
    """Why a project folder must not be used, or None. Under /tmp or outside the registry's roots
    (the client's projects_root and design system) is refused unless AEM_SANDBOX=1."""
    if sandbox_allowed():
        return None
    real = _real(pdir)
    for t in TMP_ROOTS:
        if _inside(real, _real(t)):
            return (f"{real} is under {t}; a project there is a test copy, not a client's folder "
                    "(set AEM_SANDBOX=1 for tests and acceptance runs)")
    roots = []
    for c in reg.get("clients", []):
        if client_id and c.get("id") != client_id:
            continue
        roots += [_real(c["projects_root"]), _real(c["design_system"])]
    if not any(_inside(real, r) for r in roots):
        return (f"{real} is outside the projects root and design system the registry names"
                + (f" for {client_id!r}" if client_id else "") + " (set AEM_SANDBOX=1 for tests)")
    return None


@dataclass
class Resolution:
    """How the project was found: source is flag, env, session pin, folder, folder (design system)."""
    source: str
    detail: str


class NoProject(AemError):
    """No project resolved. status and context turn this into a plain 'no project' answer."""


NO_PROJECT_HINT = ("Work from inside the project's folder, or set AEM_PROJECT=<client>/<project>. "
                   "In Claude Code, /aem use <client>/<project> pins one to the session. "
                   "A folder resolves only if the registry lists it (registry projects, or the design system).")


def from_folder(reg: dict, cwd: str | os.PathLike) -> tuple[Client, str | None, Path | None, Resolution] | None:
    """(c) The registered project whose folder contains cwd (the longest match across clients), or
    the client whose design system contains it (client only)."""
    here = _real(cwd)
    best = None
    for c in reg.get("clients", []):
        client = Client(c, reg)
        for name, entry in client.project_entries().items():
            d = _real(client.projects_root / entry["dir"])
            if _inside(here, d) and (best is None or len(d.parts) > len(best[2].parts)):
                best = (client, name, d)
    if best:
        client, name, d = best
        return client, name, d, Resolution("folder", f"the working folder is inside registered project {client.id}/{name} ({d})")
    for c in reg.get("clients", []):
        client = Client(c, reg)
        if _inside(here, _real(client.design_system)):
            return client, None, None, Resolution(
                "folder (design system)", f"the working folder is inside {client.id}'s design system; no project")
    return None


@dataclass
class Context:
    registry_path: Path
    registry: dict
    client: Client
    project: str | None = None
    project_dir: Path | None = None
    fps: Fraction | None = None
    fps_source: str | None = None
    resolution: Resolution = field(default_factory=lambda: Resolution("none", ""))
    registry_source: str = "the repo default"

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
            "resolution": {
                "source": self.resolution.source,
                "detail": self.resolution.detail,
                "project": f"{self.client.id}/{self.project}" if self.project else None,
                "folder": str(self.project_dir) if self.project_dir else None,
                "design_system": f"client {self.client.id}'s entry in the registry",
                "fps": self.fps_source,
                "registry": self.registry_source,
            },
        }


def registry_source(explicit: str | None = None) -> str:
    if explicit:
        return "--registry"
    return "AEM_REGISTRY" if os.environ.get("AEM_REGISTRY") else "the repo default"


def split_spec(spec: str, where: str) -> tuple[str, str]:
    if "/" not in spec or not all(p.strip() for p in spec.split("/", 1)):
        raise AemError(f"{where} must be <client>/<project>, not {spec!r}", hint="For example: joel/P2")
    client_id, project = spec.split("/", 1)
    return client_id.strip(), project.strip()


def _from_env(reg: dict) -> tuple[Client, str, Path, Resolution] | None:
    """(a) AEM_PROJECT, which is also how the plugin hands its session pin to every aem call it makes
    (b): the plugin sets AEM_PROJECT_SOURCE=session-pin so the answer says which it was."""
    spec = os.environ.get("AEM_PROJECT")
    if not spec:
        return None
    client_id, name = split_spec(spec, "AEM_PROJECT")
    client = find_client(reg, client_id)
    name, pdir = resolve_project(client, name)
    if os.environ.get("AEM_PROJECT_SOURCE") == "session-pin":
        return client, name, pdir, Resolution("session pin", f"pinned for this session with /aem use: {client.id}/{name}")
    return client, name, pdir, Resolution("env", f"AEM_PROJECT={spec}")


def context(args, *, require_project: bool = True, cwd: str | os.PathLike | None = None) -> Context:
    """The client and project a command acts on, in this order:
      (a) AEM_PROJECT=<client>/<project> in this process's environment;
      (b) the plugin's session pin, which the plugin passes as (a) with AEM_PROJECT_SOURCE=session-pin;
      (c) the working directory (cwd, default the process's): the registered project whose folder
          contains it (longest match), else the client whose design system contains it;
      (d) nothing: NoProject.
    --client/--project on the command line override the project part, and say so.
    The registry is AEM_REGISTRY, --registry or the repo default; it is never read from stored state.
    """
    reg_arg = getattr(args, "registry", None)
    rpath = registry_path(reg_arg)
    reg = load_registry(rpath)
    rsrc = registry_source(reg_arg)
    flag_client = getattr(args, "client", None)
    flag_project = getattr(args, "project", None)

    base = _from_env(reg) or from_folder(reg, cwd or os.getcwd())
    client, project, pdir, how = (base if base else (None, None, None, Resolution("none", "")))

    if flag_client or flag_project:
        flag_client = flag_client or (client.id if client else None)
        if not flag_client:
            raise AemError("--project needs --client when no client is resolved from the environment or the folder")
        if client is None or client.id != flag_client:
            client, project, pdir = find_client(reg, flag_client), None, None
        if flag_project:
            project, pdir = resolve_project(client, flag_project)
        how = Resolution("flag", "--client/--project on the command line")

    if client is None:
        raise NoProject("no project resolved here", hint=NO_PROJECT_HINT)
    if project is None and require_project:
        raise NoProject(f"no project resolved here: the working folder is in {client.id}'s design system, not in a project",
                        hint=NO_PROJECT_HINT)
    rate = source = None
    if pdir is not None:
        problem = folder_problem(reg, client.id, pdir)
        if problem:
            raise AemError(f"refusing project {client.id}/{project}: {problem}")
        if require_project and not pdir.is_dir():
            raise AemError(f"project folder is not readable: {pdir}", hint="Is the drive mounted?")
        try:
            found = fpsmod.resolve(pdir)
            rate, source = found["fps"], found["source"]
        except AemError:
            pass
    return Context(rpath, reg, client, project, pdir, rate, source, how, rsrc)


def use(spec: str, *, registry: str | None = None) -> dict:
    """Check that <client>/<project> resolves from the registry, has a stated frame rate and may be
    used, and write the last-used hint. Nothing else is stored: the project a command acts on is
    never read back from here."""
    client_id, name = split_spec(spec, "the project")
    reg = load_registry(registry_path(registry))
    client = find_client(reg, client_id)
    project, pdir = resolve_project(client, name)
    problem = folder_problem(reg, client.id, pdir)
    if problem:
        raise AemError(f"refusing project {client.id}/{project}: {problem}")
    rate = fpsmod.resolve(pdir)
    write_hint(client.id, project, pdir)
    return {
        "client": client.id,
        "project": project,
        "project_dir": str(pdir),
        "design_system": str(client.design_system),
        "registry": str(registry_path(registry)),
        "fps": fpsmod.rate_dict(rate["fps"], rate["source"]),
        "fps_candidates": rate["candidates"],
        "set_at": ts(),
    }
