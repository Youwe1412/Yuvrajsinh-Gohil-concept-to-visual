"""Test helpers: a throwaway client, design system and project, and synthetic renders.

Nothing here touches a real client folder: every test builds its world in a temp directory
and points AEM_HOME and the registry at it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AEM = REPO / "cli" / "bin" / "aem"
sys.path.insert(0, str(REPO / "cli"))

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
        self.env = {**os.environ, "AEM_HOME": str(self.home)}
        self.env.pop("AEM_REGISTRY", None)
        self.env.pop("AEM_FIXED_NOW", None)

    def run(self, *args, stdin: str | None = None, env: dict | None = None, check: bool = False):
        """Run the CLI with --json; returns (exit code, parsed JSON)."""
        e = {**self.env, **(env or {})}
        p = subprocess.run([sys.executable, str(AEM), *args, "--json"], input=stdin, capture_output=True,
                           text=True, env=e, cwd=str(self.tmp))
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            raise AssertionError(f"not JSON from aem {' '.join(args)}:\nstdout={p.stdout}\nstderr={p.stderr}")
        if check and p.returncode != 0:
            raise AssertionError(f"aem {' '.join(args)} exited {p.returncode}: {data}")
        return p.returncode, data

    def use(self, extra=()):
        return self.run("use", "acme/P1", "--registry", str(self.registry), *extra, check=True)

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
