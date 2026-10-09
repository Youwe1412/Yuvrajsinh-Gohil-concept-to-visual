#!/usr/bin/env python3
"""Build docs/showcase/ from AEM's evidence folders.

Usage:
  python3 docs/tools/showcase.py <moments.json> <events.jsonl> <project folder> <out dir> [<as-of text>]

For every moment whose treatment is "animation", copies up to four readable poses and the
fastest-transition strip from the latest evidence folder (reviews/<moment>/vNN/), downscaled
with ffmpeg, and writes <out dir>/README.md. Footage, screen recordings and the client's
re-typeset terminal moments are left out on purpose: the showcase holds only what this pipeline
drew.
"""
import json, os, re, subprocess, sys

mj, evp, P2, OUT = sys.argv[1:5]
asof = sys.argv[5] if len(sys.argv) > 5 else "9 Oct 2026"

j = json.load(open(mj))
ms = [m for m in j["moments"] if str(m.get("name", "")).startswith("cc_S")]
rc, ev = {}, {}
for line in open(evp):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("event") == "render_check":
        rc[e["render"]] = e
    elif e.get("event") == "evidence":
        ev[e["render"]] = e
latest = {}
for r, e in rc.items():
    latest[e["scene"]] = max(latest.get(e["scene"], ""), r)


def shrink(src, dst, width, q):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"scale={width}:-2", "-q:v", str(q), dst], check=True)
    return os.path.getsize(dst)


def anchor(n):
    return n.lower().replace("_", "").replace("-", "")


rows, total = [], 0
for m in ms:
    n = m["name"]
    is_overlay = latest.get(n, "").endswith(".mov")
    if m.get("treatment") != "animation" and not is_overlay:
        continue
    d = os.path.join(P2, "reviews", n)
    if not os.path.isdir(d):
        continue
    vs = sorted(x for x in os.listdir(d) if re.match(r"v\d+$", x))
    if not vs:
        continue
    v = vs[-1]
    vd = os.path.join(d, v)
    pd = os.path.join(vd, "poses")
    poses = sorted(f for f in os.listdir(pd) if f.endswith(".png") and not f.startswith("._")) if os.path.isdir(pd) else []
    od = os.path.join(OUT, n)
    os.makedirs(od, exist_ok=True)
    k = min(4, len(poses))
    pick = [poses[round(i * (len(poses) - 1) / (k - 1))] for i in range(k)] if k > 1 else poses[:1]
    outs = []
    for f in pick:
        o = os.path.join(od, f.replace(".png", ".jpg"))
        total += shrink(os.path.join(pd, f), o, 960, 4)
        outs.append(os.path.basename(o))
    strip = os.path.join(vd, "strip.jpg")
    has_strip = os.path.exists(strip)
    if has_strip:
        total += shrink(strip, os.path.join(od, "strip.jpg"), 1280, 5)
    r = latest.get(n)
    # prefer the newest render on disk when it is newer than the last checked one
    rd = os.path.join(P2, "renders")
    disk = sorted(f for f in os.listdir(rd) if f.startswith(n + "_v") and f.endswith((".mp4", ".mov")) and not f.startswith("._")) if os.path.isdir(rd) else []
    disk_latest = ("renders/" + disk[-1]) if disk else None
    unchecked = bool(disk_latest and r and disk_latest > r)
    note = ev.get(r, {}).get("note", "") if r else ""
    mm = re.search(r"sync max offset (\d+)f", note)
    sync = f"{mm.group(1)}f" if mm else "not measured"
    words = m.get("words") or ""
    if len(words) > 110:
        words = words[:110] + "…"
    rows.append(dict(n=n, job=m.get("job") or "-", words=words, r=r.split("/")[-1] if r else "-",
                     res=(rc[r]["result"] if r else "-") + (f" (newer {disk_latest.split('/')[-1]} on disk, not yet checked)" if unchecked else ""),
                     sync=sync, np=len(poses), v=v, outs=outs, overlay=is_overlay,
                     strip=has_strip, why=(m.get("why") or "")[:220]))

L = [
    "# P2 showcase · the animations, as AEM's evidence shows them",
    "",
    f"Status as of {asof}. Each moment below is an animation this pipeline built for Joel Belton's Claude Code video (P2). "
    "The frames are **readable poses** that `aem evidence` extracted from the latest checked render (a pose is where the picture "
    "settles for a quarter second), downscaled to 960 px, plus the **strip** of frames around the fastest transition. "
    "Nothing here is Joel's footage or his terminal; those moments are left out on purpose. Three moments (promise, exceptions, model-fit) are alpha overlays drawn over his face, rendered as ProRes 4444 `.mov`; their proxies are flattened on black. The renders themselves "
    "(3840x2160, 25 fps) stay in the project folder; where a 1080p proxy is linked, GitHub plays it on the file page. Max sync is the largest offset, in frames, between a cue word's onset "
    "and the pose settling on it.",
    "",
    f"{len(rows)} moments ({sum(1 for x in rows if x['overlay'])} alpha overlays). Measured state: [P2-STATUS.md](../P2-STATUS.md); method: [CASE-STUDY.md](../CASE-STUDY.md). "
    f"Built by `docs/tools/showcase.py`.",
    "",
    "| Moment | Teaching job | Latest render | Check | Max sync | Poses | Video |",
    "|---|---|---|---|---|---:|---|",
]
for x in rows:
    v = f"[1080p](video/{x['n']}.mp4)" if os.path.exists(os.path.join(OUT, "video", x["n"] + ".mp4")) else "-"
    L.append(f"| [{x['n']}](#{anchor(x['n'])}) | {x['job']} | `{x['r']}` | {x['res']} | {x['sync']} | {x['np']} | {v} |")
L.append("")
for x in rows:
    vid = os.path.join(OUT, "video", x["n"] + ".mp4")
    L += [f"## {x['n']}", "",
          f"**Teaching job:** {x['job']}. **On his words:** \"{x['words']}\"", "",
          f"**Why (from the plan):** {x['why']}", "",
          f"Latest render `{x['r']}` · check {x['res']} · max sync {x['sync']} · evidence {x['v']}, {x['np']} readable poses."
          + (f" **[Watch the 1080p proxy](video/{x['n']}.mp4)** (GitHub plays it on the file page)." if os.path.exists(vid) else ""), "",
          " ".join(f"![{x['n']} {o}]({x['n']}/{o})" for o in x["outs"]), ""]
    if x["strip"]:
        L += [f"Fastest transition: ![strip]({x['n']}/strip.jpg)", ""]
open(os.path.join(OUT, "README.md"), "w").write("\n".join(L) + "\n")
print(f"showcase: {len(rows)} moments, {total // 1024} KB of images")
