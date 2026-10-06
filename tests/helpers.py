"""Test helpers: a throwaway client, design system and project, and synthetic renders.

Nothing here touches a real client folder: every test builds its world in a temp directory
and points AEM_HOME and the registry at it. Importing this module also points the whole test
process at a fresh AEM_HOME and a temp copy of the registry, so a test that forgets its world
still never reads or writes the operator's ~/.aem or registry/clients.json; and it snapshots
both, so test_zz_isolation can fail the run if either changed.
"""
from __future__ import annotations

import atexit
import contextlib
import json
import os
import pty
import secrets
import time
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AEM = REPO / "cli" / "bin" / "aem"
sys.path.insert(0, str(REPO / "cli"))

import isolation  # noqa: E402  (tests/isolation.py)
from aem import operator as aem_operator  # noqa: E402

REAL_STATE_BEFORE = isolation.snapshot()
SANDBOX = isolation.sandbox(prefix="aem-tests-")
os.environ.update(SANDBOX.env)
for _name in ("AEM_FIXED_NOW", "AEM_PROJECT", "AEM_PROJECT_SOURCE", "AEM_OPERATOR_NONCE"):
    os.environ.pop(_name, None)
atexit.register(SANDBOX.cleanup)

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

LABELLED_HEADER = {
    "_comment": "Test client critic labelled cases.",
    "fields": {"case_id": "", "status": "", "video": "", "shot": "", "word_ids": "", "render_sha256": "",
               "frames_or_crops": "", "ruling": "", "acme_words": "", "ruling_date": "", "source": "",
               "rule_ids": "", "critic_verdict_g5": "", "critic_agreed": "", "notes": ""},
}

DECISIONS = """# Acme decisions

The client's own words, newest first.

Rules for this file:

- Quote verbatim.

---

## 2026-09-01 · P0 · Email

> "Keep it calm."

| What he said | Scope |
|---|---|
| Calm | Channel |
"""

RULES = """# Acme rules index

## Acme's stated preferences

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| A-01 | Calm motion | Client default | C | Client stated | Brief |
| A-02 | No stock | Client default | C | Client stated | Brief |

## Motion

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| M-03 | Land on the word | Default | E | Measured | Motion 02 |
| M-T1-01 | Seekable | Invariant | P | Measured | Motion 06 |
"""


class World:
    """A temp client 'acme' with a design system, a project 'P1 - Test' and an isolated AEM_HOME."""

    def __init__(self, fps: str | None = "24000/1001", fps_in: str = "frame.md"):
        self.tmp = Path(tempfile.mkdtemp(prefix="aem-test-"))
        self.home = self.tmp / "home"
        self.ds = self.tmp / "Acme" / "00 - Acme Design System"
        self.root = self.tmp / "Acme"
        self.project = self.root / "P1 - Test"
        self.skills = self.tmp / "skills"
        for d in (self.home, self.ds / "critic", self.ds / "text", self.ds / "Skill" / "acme-studio",
                  self.project / "compositions", self.project / "renders", self.project / "data",
                  self.skills / "acme-studio"):
            d.mkdir(parents=True, exist_ok=True)
        (self.ds / "acme-decisions.md").write_text(DECISIONS, encoding="utf-8")
        (self.ds / "rules.md").write_text(RULES, encoding="utf-8")
        (self.ds / "critic" / "labelled-cases.jsonl").write_text(json.dumps(LABELLED_HEADER) + "\n", encoding="utf-8")
        skill = "# Acme studio\n\nCite A-01 and M-03 and M-T1-01.\n"
        (self.ds / "Skill" / "acme-studio" / "SKILL.md").write_text(skill, encoding="utf-8")
        (self.skills / "acme-studio" / "SKILL.md").write_text(skill, encoding="utf-8")
        page = "<html><body><h1>Acme Motion</h1></body></html>"
        (self.ds / "Acme - Motion System.html").write_text(page, encoding="utf-8")
        import hashlib
        h = hashlib.sha256(page.encode()).hexdigest()[:16]
        (self.ds / "text" / "Acme - Motion System.md").write_text(
            f"Generated from Acme - Motion System.html (SHA-256 {h}) on 2026-10-06. Do not edit.\n\n# Acme Motion\n",
            encoding="utf-8")
        if fps:
            if fps_in == "frame.md":
                (self.project / "frame.md").write_text(f'---\nfps           : "{fps}"\n---\n', encoding="utf-8")
            elif fps_in == "settings":
                (self.project / "aem.project.json").write_text(json.dumps({"fps": fps}), encoding="utf-8")
        self.registry = self.tmp / "clients.json"
        self.registry.write_text(json.dumps({
            "version": 1,
            "operator": {"id": "yuvraj", "name": "Yuvraj"},
            "shared_paths": [],
            "clients": [{
                "id": "acme", "name": "Acme Learning", "contact": "Ada",
                "design_system": str(self.ds), "projects_root": str(self.root),
                "projects": {"P1": {"dir": "P1 - Test"}},
                "decisions_file": "acme-decisions.md", "rules_file": "rules.md", "preference_prefix": "A",
                "labelled_cases_file": "critic/labelled-cases.jsonl", "text_dirs": ["text"],
                "skill": "acme-studio", "skill_master": "Skill/acme-studio",
                "gates": {"G1": "Inputs", "G2": "Plan", "G3": "Stills", "G4": "Rough render",
                          "G5": "Critique", "G6": "Deliver", "G7": "Client review"},
                "waiting_on_client_ids": ["acme", "ada"],
                "protected_files": {"design_system": ["acme-decisions.md", "rules.md", "critic/labelled-cases.jsonl"],
                                    "project": ["approvals.jsonl", "events.jsonl"]},
                "blocked_commands": ["snapshot --describe"], "idle_minutes": 10,
            }],
        }, indent=2), encoding="utf-8")
        self.env = {**os.environ, "AEM_HOME": str(self.home), "AEM_REGISTRY": str(self.registry), "AEM_SANDBOX": "1"}
        for name in ("AEM_FIXED_NOW", "AEM_PROJECT", "AEM_PROJECT_SOURCE", "AEM_OPERATOR_NONCE"):
            self.env.pop(name, None)

    @contextlib.contextmanager
    def environ(self):
        """This world's AEM_HOME and registry for in-process calls; restores the process sandbox after."""
        saved = {k: os.environ.get(k) for k in ("AEM_HOME", "AEM_REGISTRY")}
        os.environ.update(AEM_HOME=str(self.home), AEM_REGISTRY=str(self.registry))
        try:
            yield
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # --- operator commands: a nonce the way the plugin makes one, or none -------------------------

    def make_nonce(self, ttl_s: float = 60.0) -> str:
        """A one-time operator nonce, written as the plugin writes it: only its SHA-256 on disk."""
        nonce = secrets.token_hex(32)
        d = self.home / "nonces"
        d.mkdir(parents=True, exist_ok=True)
        (d / aem_operator.nonce_hash(nonce)).write_text(json.dumps({"expires_at": time.time() + ttl_s}), encoding="utf-8")
        return nonce

    def _env_for(self, args, env, operator):
        e = {**self.env, **(env or {})}
        name = aem_operator.command_name(args[0], args[1] if len(args) > 1 else None) if args else None
        if name and operator is not False and "AEM_OPERATOR_NONCE" not in e:
            e["AEM_OPERATOR_NONCE"] = self.make_nonce()
        return e

    def run(self, *args, stdin: str | None = None, env: dict | None = None, check: bool = False,
            cwd: Path | str | None = None, operator: bool | None = None):
        """Run the CLI with --json; returns (exit code, parsed JSON). It runs in the project folder, so
        the project resolves from the folder as it does for a session started there; pass cwd=self.tmp
        for a process that is in no project. An operator-only command gets a valid one-time nonce, as
        the plugin's slash command would give it, unless operator=False (then it has none, as an agent
        has none)."""
        e = self._env_for(args, env, operator)
        p = subprocess.run([sys.executable, str(AEM), *args, "--json"], input=stdin, capture_output=True,
                           text=True, env=e, cwd=str(cwd if cwd is not None else self.project))
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            raise AssertionError(f"not JSON from aem {' '.join(args)}:\nstdout={p.stdout}\nstderr={p.stderr}")
        if check and p.returncode != 0:
            raise AssertionError(f"aem {' '.join(args)} exited {p.returncode}: {data}")
        return p.returncode, data

    def run_raw(self, *args, stdin: str | None = None, env: dict | None = None, cwd: Path | str | None = None,
                operator: bool | None = None):
        """The CLI without --json, for argument errors and text output: a CompletedProcess."""
        e = self._env_for(args, env, operator)
        return subprocess.run([sys.executable, str(AEM), *args], input=stdin, capture_output=True, text=True, env=e,
                              cwd=str(cwd if cwd is not None else self.project))

    def run_tty(self, *args, env: dict | None = None, cwd: Path | str | None = None, keep_markers: bool = False,
                keyboard: str | None = None):
        """Run the CLI as it runs in the operator's Terminal: stdin, stdout and stderr on a real pseudo-terminal
        that is the process's controlling terminal. Returns (exit code, output). The agent markers
        (CLAUDECODE, CODEX_CI, ...) are removed from its environment, as the operator's terminal has none,
        unless keep_markers=True (then it is an agent that allocated a terminal). No nonce is given."""
        e = dict(self.env)
        e.pop("AEM_OPERATOR_NONCE", None)
        if not keep_markers:
            for name in aem_operator.AGENT_MARKERS:
                e.pop(name, None)
        e.update(env or {})
        pid, fd = pty.fork()
        if pid == 0:  # the child: stdin, stdout, stderr are the terminal, and it is the controlling terminal
            try:
                os.chdir(str(cwd if cwd is not None else self.project))
                os.execve(sys.executable, [sys.executable, str(AEM), *args], e)
            finally:
                os._exit(127)
        if keyboard is not None:
            os.write(fd, keyboard.encode())
        out = b""
        while True:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        _, status = os.waitpid(pid, 0)
        os.close(fd)
        return os.waitstatus_to_exitcode(status), out.decode("utf-8", "replace")

    def use(self, extra=()):
        """The last-used hint for acme/P1. Commands do not need it: the project resolves from the folder."""
        return self.run("use", "acme/P1", *extra, check=True)

    def events(self):
        p = self.project / "events.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def approvals(self):
        p = self.project / "approvals.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def make_video(path: Path, *, frames: int = 50, fps: str = "25", size: str = "320x180", box: str | None = None,
               color: str = "0x202020", codec: str = "libx264", pix_fmt: str = "yuv420p", graph: str | None = None) -> Path:
    """A synthetic clip: flat background, optional drawbox filter (flashes) or a whole lavfi graph (motion)."""
    vf = []
    if box:
        vf.append(box)
    source = graph or f"color=c={color}:s={size}:r={fps}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source, "-frames:v", str(frames)]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", codec, "-pix_fmt", pix_fmt]
    if codec == "libx264":
        cmd += ["-crf", "12", "-preset", "veryfast"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True)
    return path


class WorldCase(unittest.TestCase):
    fps = "24000/1001"
    fps_in = "frame.md"

    def setUp(self):
        self.w = World(self.fps, self.fps_in)

    def tearDown(self):
        self.w.cleanup()
