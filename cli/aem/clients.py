"""Client-level records: what the client said, operator overrides, and new clients."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import ledger
from .registry import Context, load_registry
from .util import AemError, REPO_ROOT, expand, sha256_text, today, ts, write_json_atomic

SCOPES = ("channel", "video", "instance")


# --- client-said -----------------------------------------------------------------------

def client_said(ctx: Context, quote: str, *, scope: str, source: str, item: str | None = None) -> dict:
    """Add a dated, verbatim entry to the client's decisions file, marked as entered by the operator."""
    quote = quote.rstrip("\n")
    if not quote.strip():
        raise AemError("no quote on standard input", hint="Paste the client's exact words, then end input.")
    scopes = ctx.client.raw.get("decision_scopes", SCOPES)
    if scope not in scopes:
        raise AemError(f"scope must be one of {', '.join(scopes)}")
    if scope == "instance" and not item:
        raise AemError("an instance-scope entry needs --item (the shot it is about)")
    path = ctx.client.decisions_path
    if not path.exists():
        raise AemError(f"decisions file not found: {path}")
    when = ts()
    scope_text = {"channel": "channel (every video)",
                  "video": f"video ({ctx.project})" if ctx.project else "video",
                  "instance": f"instance ({ctx.project} · {item})"}.get(scope, scope)
    quoted = [("> " + line) if line else ">" for line in quote.split("\n")]
    heading = f"## {today()} · {ctx.project or ctx.client.name} · {source}"
    entry = [
        heading, "",
        *quoted, "",
        "| Scope | Source | Entered |",
        "|---|---|---|",
        f"| {scope_text} | {source} | entered by {ctx.client.operator} with `aem client-said`, {when} |",
        "",
        "Our reading: not yet written. Quote copied verbatim from what was pasted.",
    ]
    original = path.read_text(encoding="utf-8")
    lines = original.split("\n")
    sep = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    if ctx.client.decisions_order == "newest_first" and sep is not None:
        block = [""] + entry + ["", "---"]
        at = sep + 1
        placed = "after the header, newest first"
    else:
        while lines and lines[-1] == "":
            lines.pop()
        block = ["", "---", ""] + entry + [""]
        at = len(lines)
        placed = "at the end"
    new_lines = lines[:at] + block + lines[at:]
    tmp = path.with_suffix(path.suffix + ".aem-tmp")
    tmp.write_text("\n".join(new_lines), encoding="utf-8")
    tmp.replace(path)
    # Read back: the quote is there verbatim and every earlier line is unchanged and in order.
    back = path.read_text(encoding="utf-8").split("\n")
    if back[at:at + len(block)] != block or back[:at] + back[at + len(block):] != lines:
        raise AemError(f"{path} did not read back as written; check it by hand")
    ledger.record(ctx, "client_said", note=f"{scope} · {source}", fill_stage=True,
                  quote_sha256=sha256_text(quote), decisions_file=str(path), source="aem client-said")
    return {"ok": True, "file": str(path), "placed": placed, "heading": heading, "scope": scope,
            "quote_sha256": sha256_text(quote), "entered_by": ctx.client.operator}


# --- allow -------------------------------------------------------------------------------

def _allow_id(target: str, when: str) -> str:
    return "allow-" + sha256_text(target + when)[:8]


def allow(ctx: Context, target: str, reason: str, *, once: bool) -> dict:
    if not reason or not reason.strip():
        raise AemError("an override needs a reason")
    when = ts()
    aid = _allow_id(target, when)
    rec = ledger.record(ctx, "allow", note=reason.strip(), target=target, allow_id=aid,
                        once=bool(once), granted_by=ctx.client.operator, source="aem allow")
    return {"ok": True, "allow_id": aid, "target": target, "once": bool(once), "reason": reason.strip(), "ts": rec["ts"]}


def revoke(ctx: Context, allow_id: str) -> dict:
    if allow_id not in {a["allow_id"] for a in active_allows(ctx)}:
        raise AemError(f"no active allow {allow_id!r}")
    ledger.record(ctx, "allow_revoked", note=None, allow_id=allow_id, source="aem allow --revoke")
    return {"ok": True, "revoked": allow_id}


def active_allows(ctx: Context) -> list[dict]:
    """Allows not yet consumed (one-time) or revoked."""
    out = {}
    for ev in ledger.read_events(ctx):
        e = ev.get("event")
        if e == "allow":
            out[ev["allow_id"]] = {"allow_id": ev["allow_id"], "target": ev.get("target"), "once": ev.get("once", False),
                                   "reason": ev.get("note"), "ts": ev.get("ts")}
        elif e == "allow_revoked" or (e == "allow_used" and out.get(ev.get("allow_id"), {}).get("once")):
            out.pop(ev.get("allow_id"), None)
    return list(out.values())


def consume_allow(ctx: Context, allow_id: str, *, subject: str, rule: str | None = None) -> dict:
    ledger.record(ctx, "allow_used", note=subject[:500], allow_id=allow_id, rule=rule, source="aem guard")
    return {"allow_id": allow_id, "subject": subject}


# --- new-client --------------------------------------------------------------------------

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
TEMPLATE = REPO_ROOT / "registry" / "client-template"


def _fill(text: str, values: dict) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def new_client(registry_path: Path, client_id: str, *, name: str, design_system: str, projects_root: str,
               contact: str | None = None, skill: str | None = None, template: Path = TEMPLATE) -> dict:
    if not ID_RE.match(client_id):
        raise AemError(f"client id {client_id!r} must be 2-32 lowercase letters, digits or hyphens")
    reg = load_registry(registry_path)
    if any(c["id"] == client_id for c in reg["clients"]):
        raise AemError(f"client {client_id!r} is already registered")
    ds = expand(design_system).resolve()
    if ds.exists() and any(p for p in ds.iterdir() if not p.name.startswith(".")):
        raise AemError(f"{ds} already has files; new-client only scaffolds into a new or empty folder")
    values = {
        "CLIENT_ID": client_id, "CLIENT_NAME": name, "CONTACT": contact or name, "DATE": today(),
        "OPERATOR": (reg.get("operator") or {}).get("name", "the operator"),
        "SKILL": skill or f"{client_id}-studio",
    }
    created = []
    ds.mkdir(parents=True, exist_ok=True)
    for src in sorted(template.rglob("*")):
        rel = src.relative_to(template)
        if rel.name == "client.json" or rel.name.startswith("._") or rel.name == ".DS_Store":
            continue
        dest = ds / Path(str(rel).replace("__CLIENT__", client_id))
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in (".md", ".jsonl", ".json", ".txt"):
            dest.write_text(_fill(src.read_text(encoding="utf-8"), values), encoding="utf-8")
        else:
            shutil.copyfile(src, dest)
        created.append(dest.relative_to(ds).as_posix())
    entry = json.loads(_fill((template / "client.json").read_text(encoding="utf-8"), values))
    entry.update({"id": client_id, "name": name, "design_system": str(ds),
                  "projects_root": str(expand(projects_root).resolve())})
    if contact:
        entry["contact"] = contact
    if skill:
        entry["skill"] = skill
    reg["clients"].append(entry)
    write_json_atomic(registry_path, reg)
    return {"ok": True, "client": client_id, "design_system": str(ds), "created": created, "registry": str(registry_path),
            "entry": entry}
