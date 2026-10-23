"""drift: places where the client's system and what the agent reads have come apart.

1. Text exports: each generated file in the design system's text/ folder names its source
   page and that page's SHA-256 in its first line. A different hash means the page changed
   after the export.
2. Skill: the installed copy (~/.claude/skills/<skill>) against the master in the design
   system (skill_master), file by file.
3. Rule IDs: every rule ID the skill cites exists in the client's rules file.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .registry import Client
from .util import sha256_file

HEADER = re.compile(r"^Generated from (?P<src>.+?) \(SHA-256 (?P<hash>[0-9a-f]{8,64})\)(?: on (?P<date>[0-9-]+))?", re.I)
DEFAULT_RULE_ID = r"\b[A-Z]{1,2}(?:-T\d)?-\d{2}\b"
IGNORE = {".DS_Store"}


def _files(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.startswith("._") and p.name not in IGNORE:
            out[p.relative_to(root).as_posix()] = p
    return out


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_text_exports(client: Client) -> list[dict]:
    findings = []
    ds = client.design_system
    text_dirs = client.raw.get("text_dirs", ["text"])
    for d in text_dirs:
        for md in sorted((ds / d).glob("*.md")) if (ds / d).is_dir() else []:
            if md.name.startswith("._"):
                continue
            with open(md, encoding="utf-8", errors="replace") as f:
                first = f.readline().strip()
            m = HEADER.match(first)
            if not m:
                continue
            src = ds / m.group("src")
            rel = md.relative_to(ds).as_posix()
            if not src.exists():
                findings.append({"check": "text-export", "file": rel, "problem": f"source page {m.group('src')} not found"})
                continue
            actual = sha256_file(src)
            if not actual.startswith(m.group("hash").lower()):
                findings.append({
                    "check": "text-export", "file": rel,
                    "problem": f"{m.group('src')} changed since the export (export says {m.group('hash')}, page is {actual[:16]})",
                    "fix": "Re-run the design system's text export tool, then rebuild the skill bundle.",
                })
    return findings


def check_skill(client: Client, skills_dir: Path) -> list[dict]:
    if not client.skill or not client.skill_master:
        return []
    master = client.skill_master
    installed = skills_dir / client.skill
    if not master.is_dir():
        return [{"check": "skill", "problem": f"skill master not found: {master}"}]
    if not installed.is_dir():
        return [{"check": "skill", "problem": f"skill {client.skill} is not installed at {installed}",
                 "fix": f"cp -R \"{master}/.\" \"{installed}/\""}]
    a, b = _files(master), _files(installed)
    findings = []
    for rel in sorted(set(a) | set(b)):
        if rel not in b:
            findings.append({"check": "skill", "file": rel, "problem": "in the master, not installed"})
        elif rel not in a:
            findings.append({"check": "skill", "file": rel, "problem": "installed, not in the master"})
        elif _digest(a[rel]) != _digest(b[rel]):
            newer = "installed copy" if b[rel].stat().st_mtime > a[rel].stat().st_mtime else "master"
            findings.append({"check": "skill", "file": rel, "problem": f"installed copy differs from the master (newer: {newer})"})
    for f in findings:
        f.setdefault("fix", f"Edit the master, then: cp -R \"{master}/.\" \"{installed}/\"")
    return findings


def rule_ids_in(text: str, pattern: str) -> set:
    return set(re.findall(pattern, text))


def check_rule_ids(client: Client, skills_dir: Path) -> list[dict]:
    pattern = client.raw.get("rule_id_pattern", DEFAULT_RULE_ID)
    rules = client.rules_path
    if not rules.exists():
        return [{"check": "rule-ids", "problem": f"rules file not found: {rules}"}]
    defined = set()
    for line in rules.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\|\s*([^|\s]+)\s*\|", line)
        if m and re.fullmatch(pattern, m.group(1)):
            defined.add(m.group(1))
    skill_root = client.skill_master if client.skill_master and client.skill_master.is_dir() else (
        skills_dir / client.skill if client.skill else None)
    if not skill_root or not skill_root.is_dir():
        return []
    texts = {rel: p.read_text(encoding="utf-8", errors="replace") for rel, p in _files(skill_root).items()
             if p.suffix.lower() in (".md", ".txt")}
    # IDs the skill defines itself, each as a Markdown heading (`### O-15 · …`): the operator's standing direction
    # in mergetomaster-studio's references/operator-direction.md. They are the skill's, not the rules file's.
    heading = re.compile(rf"^#{{1,6}}\s+({pattern})\b", re.M)
    defined |= {m.group(1) for text in texts.values() for m in heading.finditer(text)}
    findings = []
    for rel, text in texts.items():
        cited = rule_ids_in(text, pattern)
        for rid in sorted(cited - defined):
            findings.append({"check": "rule-ids", "file": rel, "rule_id": rid,
                             "problem": f"{rid} is cited by the skill but not defined in {client.raw['rules_file']}"})
    return findings


def drift(client: Client, skills_dir: Path) -> dict:
    findings = check_text_exports(client) + check_skill(client, skills_dir) + check_rule_ids(client, skills_dir)
    return {"ok": not findings, "client": client.id, "findings": findings,
            "checked": ["text exports vs their HTML pages", "installed skill vs master", "skill rule IDs vs rules file"]}
