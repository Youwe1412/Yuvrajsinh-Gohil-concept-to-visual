"""Client-level records: what the client said, and new clients."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import integrity, ledger, operator
from .registry import Context, load_registry
from .util import AemError, REPO_ROOT, expand, sha256_text, today, ts, write_json_atomic

SCOPES = ("channel", "video", "instance")


# --- client-said -----------------------------------------------------------------------

HOW_TYPED = {"terminal": "in a terminal", "slash command": "with /client-said in Claude Code"}


QUOTE_MATCH_MIN = 20  # shorter quotes ("ok", "love it") are never taken to be one already in the file


def entry_quoting(path: Path, quote: str) -> str | None:
    """The heading of the decisions-file entry that already quotes these words, if one does (whitespace and line
    breaks aside; quotation marks around the words aside)."""
    from . import recall
    want = " ".join(quote.split()).strip('"\u201c\u201d ')
    if len(want) < QUOTE_MATCH_MIN:
        return None
    for sec in recall.sections(path):
        if want in " ".join(" ".join(recall.quotes(sec["body"])).split()):
            return sec["heading"]
    return None


def client_said(ctx: Context, quote: str, *, scope: str | None, source: str, item: str | None = None,
                about: str | None = None, ruling: str | None = None) -> dict:
    """Add a dated entry to the client's decisions file: the quote exactly as typed, and who typed it. With --about
    (a moment, `video` or `channel`) the quote is also the client's ruling at that level in the labelled cases; a
    quote the decisions file already has is not written again, and the ruling names the entry that has it."""
    operator.assert_checked("client-said")
    quote = quote.rstrip("\n")
    if not quote.strip():
        raise AemError("no quote on standard input", hint="Paste the client's exact words, then end input.")
    if ruling and not about:
        raise AemError("--ruling goes with --about <moment>: it is the client's keep, change or remove on that moment")
    if about:
        derived = about if about in ("video", "channel") else "instance"
        if scope and scope != derived:
            raise AemError(f"--about {about} is a {derived}-level quote; leave --scope out or make it {derived}")
        scope = derived
        if derived == "instance":
            item = item or about
    if not scope:
        raise AemError("client-said needs --scope channel|video|instance, or --about <moment|video|channel>")
    if about:  # what --about names is checked before anything is written
        from . import rulings
        rulings.check_about(ctx, about, ruling)
    scopes = ctx.client.raw.get("decision_scopes", SCOPES)
    if scope not in scopes:
        raise AemError(f"scope must be one of {', '.join(scopes)}")
    if scope == "instance" and not item:
        raise AemError("an instance-scope entry needs --item (the shot it is about)")
    path = ctx.client.decisions_path
    if not path.exists():
        raise AemError(f"decisions file not found: {path}")
    existing = entry_quoting(path, quote) if about else None
    if existing:
        from . import rulings
        ledger.record(ctx, "client_said", note=f"{scope} · {source} · already in \"{existing}\"", fill_stage=True,
                      quote_sha256=sha256_text(quote), decisions_file=str(path), typed_by=ctx.client.operator,
                      via=operator.via(), about=about, ruling=ruling, decisions_entry=existing, source="aem client-said")
        case = rulings.about(ctx, about, quote, ruling=ruling, source=source, entry=existing)
        return {"ok": True, "file": str(path), "placed": f"already in the entry \"{existing}\"; not written again",
                "heading": f"## {existing}", "scope": scope, "quote_sha256": sha256_text(quote),
                "entered_by": ctx.client.operator, "via": operator.via(), "about": about, "case": case,
                "existing_entry": existing}
    when = ts()
    scope_text = {"channel": "channel (every video)",
                  "video": f"video ({ctx.project})" if ctx.project else "video",
                  "instance": f"instance ({ctx.project} · {item})"}.get(scope, scope)
    how = (" " + HOW_TYPED[operator.via()]) if operator.via() in HOW_TYPED else ""
    quoted = [("> " + line) if line else ">" for line in quote.split("\n")]
    heading = f"## {today()} · {ctx.project or ctx.client.name} · {source}"
    entry = [
        heading, "",
        *quoted, "",
        "| Scope | Source | Entered |",
        "|---|---|---|",
        f"| {scope_text} | {source} | typed by {ctx.client.operator}{how} (`aem client-said`), {when} |",
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
    integrity.ensure_baseline(path)  # on AEM's first write the text already there is the baseline
    tmp = path.with_suffix(path.suffix + ".aem-tmp")
    tmp.write_text("\n".join(new_lines), encoding="utf-8")
    tmp.replace(path)
    # Read back: the quote is there verbatim and every earlier line is unchanged and in order.
    back = path.read_text(encoding="utf-8").split("\n")
    if back[at:at + len(block)] != block or back[:at] + back[at + len(block):] != lines:
        raise AemError(f"{path} did not read back as written; check it by hand")
    integrity.note_insert(path, original, at, block, by="aem client-said")
    ledger.record(ctx, "client_said", note=f"{scope} · {source}", fill_stage=True,
                  quote_sha256=sha256_text(quote), decisions_file=str(path), typed_by=ctx.client.operator,
                  via=operator.via(), about=about, ruling=ruling, source="aem client-said")
    case = None
    if about:
        from . import rulings
        case = rulings.about(ctx, about, quote, ruling=ruling, source=source, entry=heading[3:])
    return {"ok": True, "file": str(path), "placed": placed, "heading": heading, "scope": scope,
            "quote_sha256": sha256_text(quote), "entered_by": ctx.client.operator, "via": operator.via(),
            "about": about, "case": case}


# --- new-client --------------------------------------------------------------------------

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")
TEMPLATE = REPO_ROOT / "registry" / "client-template"


def _fill(text: str, values: dict) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def new_client(registry_path: Path, client_id: str, *, name: str, design_system: str, projects_root: str,
               contact: str | None = None, skill: str | None = None, template: Path = TEMPLATE) -> dict:
    operator.assert_checked("new-client")
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
