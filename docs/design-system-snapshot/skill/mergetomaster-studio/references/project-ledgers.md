# Project ledgers: approvals and time

Two append-only JSON Lines files in the project folder. Append; never rewrite a past line.

## approvals.jsonl: approvals tied to the exact render

After Yuvraj approves at **G4** or **G6**, append one line per approved scene:

```json
{"gate": "G4", "scene": "fd_S04_50ms", "render": "renders/v09/fd_S04_50ms_v09.mp4", "render_sha256": "<64 hex>", "source_revision": "<git commit, or SHA-256 of the scene source>", "approver": "Yuvraj", "date": "2026-10-06"}
```

Use the path relative to the project folder, and the full SHA-256 of the file as it was reviewed.

**The check.** Before placing a master in an FCPXML (`references/fcpxml-delivery.md`) or delivering
it, hash the file and find the latest approval for that scene at that gate. No approval, or a
different SHA-256, means stop: a changed render needs a fresh approval, however small the change.

This is a recorded check that keeps us honest about what was approved, **not a security boundary**:
anyone with the drive can edit the file.

## events.jsonl: time per stage

At every gate start and finish, and whenever work stops for someone else, append:

```json
{"ts": "2026-10-06T14:05:00+05:30", "gate": "G2", "scene": null, "event": "start", "note": "shot list from visual plan"}
```

`event` is one of `start`, `finish`, `waiting_on_yuvraj`, `waiting_on_joel`, `blocked`. Use the local
time with its offset. `scene` is null for whole-video work. A wait ends at the next `start` or
`finish` for that gate.

## reports/time.md

At **G6** and **G7**, summarise `events.jsonl` into `reports/time.md`:

- minutes per gate and per scene, counting active time (from `start` to `finish`, minus waits);
- waiting on Yuvraj, waiting on Joel and blocked time, each shown separately;
- idle time (gaps with no open gate) shown separately, never counted as work;
- any gate with a `start` and no `finish`, listed as open.

Say how the numbers were computed. They are for planning the next video, not for billing.
