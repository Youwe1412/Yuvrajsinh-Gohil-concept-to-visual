import json,sys,re,collections
moments_json, events_path, time_md, out = sys.argv[1:5]
j=json.load(open(moments_json))
ms=[m for m in j["moments"] if str(m.get("name","")).startswith("cc_S")]
artefacts=len(j["moments"])-len(ms)
rc={};ev={};approved={}
for line in open(events_path):
    try: e=json.loads(line)
    except: continue
    if e.get("event")=="render_check": rc[e["render"]]=e
    elif e.get("event")=="evidence": ev[e["render"]]=e
    elif e.get("event")=="approval": approved[e.get("render")]=e
latest={}
for r,e in rc.items():
    s=e["scene"]
    if s not in latest or r>latest[s]: latest[s]=r
flash_renders=[r for r,e in rc.items() if e.get("flashes")]
def sync(r):
    n=ev.get(r,{}).get("note","")
    m=re.search(r"sync max offset (\d+)f",n)
    return f"{m.group(1)}f" if m else ("not measured" if r in ev else "-")
rows=[]
treat=collections.Counter()
for m in ms:
    t=m.get("treatment") or "-"; treat[t]+=1
    name=m["name"]; r=latest.get(name)
    ws=m.get("word_ids") or []
    span=f"{ws[0]}–{ws[-1]}" if ws else "-"
    nver=len([x for x in rc if rc[x]["scene"]==name])
    fl="yes" if r in flash_renders else ("no" if r else "-")
    app="yes" if r in approved else "-"
    rows.append(f"| {name} | {span} | {m.get('job') or '-'} | {t} | {r.split('/')[-1] if r else '-'} | {nver or '-'} | {rc[r]['result'] if r else '-'} | {fl} | {sync(r) if r else '-'} | {app} |")
built=len(latest)
L=[]
L.append("# P2 status · Claude Code video · MergeToMaster")
L.append("")
L.append("Status as of 7 Oct 2026, 23:50 IST. Generated from `aem moments` (`moments/index.json`), `aem report` (`reports/time.md`) and `events.jsonl` in the P2 project folder by `docs/tools/p2status.py`. Joel's Frame.io review is pending; this page is updated after it.")
L.append("")
L.append("## Counts (measured by AEM unless marked)")
L.append("")
L.append(f"- Named moments in the plan: **{len(ms)}** (`aem moments` lists {len(j['moments'])} rows; the other {artefacts} are table headings and scene labels it read from `visual-plan.md` and `shotlist.md`, a parsing defect noted in CASE-STUDY §g).")
L.append(f"- Treatments: " + ", ".join(f"{k} {v}" for k,v in treat.most_common()) + ".")
L.append(f"- Direction: {j.get('direction')} ({j.get('notes',0)} notes from Joel); asked {j.get('asked')}, added {j.get('added')} (every moment is ours to decide).")
L.append(f"- Moments with at least one render checked: **{built}**; render versions checked: **{len(rc)}**; check failures: **{sum(1 for e in rc.values() if e['result']!='pass')}**.")
L.append(f"- Evidence runs (`aem evidence`): **{len(ev)}** renders.")
L.append(f"- Render versions where `check-render` flagged one- or two-frame luma flashes (area 0.02–0.04 % of frame): **{len(flash_renders)}**; the evidence notes record no flash for any render.")
L.append(f"- Standing approvals: **{len(approved)}** (" + ", ".join(e.get('render','').split('/')[-1]+f" · {e.get('via')}" for e in approved.values()) + ").")
L.append(f"- Rulings from Joel on P2: **0** (review pending).")
L.append("")
L.append("## Time per gate (measured by AEM, `aem report`)")
L.append("")
tm=open(time_md).read()
sec=tm.split("## Per gate\n")[1].split("## Per gate and scene")[0].strip()
L.append(sec)
L.append("")
L.append("Per-moment time: none attributable. Every stage so far was whole-video (`G2 · (whole video)`, `G4 · (whole video)`), so `aem report` leaves 7:07:00 unattributed and spreads nothing across moments. Observed session time outside any stage: 16:00:10 of 23:07:09 observed. Three stages were inferred by AEM from file changes (one G2, two G4).")
L.append("")
L.append("## Moments")
L.append("")
L.append("Latest render per moment; sync is the maximum word-to-cue offset in frames at 25 fps from the evidence run on that render.")
L.append("")
L.append("| Moment | Words | Teaching job | Treatment | Latest render | Versions | Check | Flash flagged | Max sync | Approved |")
L.append("|---|---|---|---|---|---:|---|---|---|---|")
L.extend(rows)
L.append("")
L.append("## Evidence summary")
L.append("")
L.append("| Render | Check | Flash flagged | Max sync | Evidence seconds |")
L.append("|---|---|---|---|---:|")
for r in sorted(rc):
    L.append(f"| {r.split('/')[-1]} | {rc[r]['result']} | {'yes' if r in flash_renders else 'no'} | {sync(r)} | {ev.get(r,{}).get('seconds','-')} |")
L.append("")
L.append("Note: at snapshot time the P2 `renders/` folder and the per-version `reviews/<moment>/vNN/` evidence folders are not on disk; the record of each check and evidence run (render SHA-256, result, flashes, sync note, seconds) is in `events.jsonl`, and the HyperFrames `check` results in `reviews/checks/<moment>.json` (30 files, 29 ok, `cc_S04_agent-file` not ok).")
open(out,"w").write("\n".join(L)+"\n")
print("rows",len(rows),"built",built,"rc",len(rc),"flash",len(flash_renders),"approved",len(approved),"treat",dict(treat))
