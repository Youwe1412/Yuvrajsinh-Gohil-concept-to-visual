"""check-render: probe a render against the project spec and scan it for one- and two-frame flashes.

The flash scan decodes every frame with ffmpeg, scaled by area averaging to a coarse grid of
luma (and alpha, when the file has it), and looks for regions that change and then return
to what they were one or two frames later, with no nearby region taking the new content
(which would be motion, not a flash). It is a heuristic with stated limits; see docs.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from . import approvals, ledger
from . import fps as fpsmod
from .registry import Context
from .util import AemError, CheckFailed, rel_to, sha256_file

GRID_W, GRID_H = 96, 54
CHANGE = 20      # block mean difference (0-255) that counts as content appearing
RETURN = 6       # block mean difference under which a block is back to before
NEAR = 12        # cells: new content this close at the next frame means motion, not a flash
MIN_AREA_PCT = 0.1  # findings smaller than this share of the frame are reported as minor, not failures
ALPHA_FMTS = ("yuva", "rgba", "argb", "bgra", "abgr", "gbrap", "ya8", "ya16", "rgba64", "bgra64")


def _need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise AemError(f"{tool} not found on PATH", hint="Install FFmpeg (brew install ffmpeg).")
    return path


def probe(path: Path) -> dict:
    cmd = [_need("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,duration",
           "-show_entries", "format=duration,format_name", "-of", "json", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise CheckFailed(f"ffprobe could not read {path.name}: {out.stderr.strip()[:300]}",
                          data={"ok": False, "path": str(path)})
    data = json.loads(out.stdout or "{}")
    streams = data.get("streams") or []
    if not streams:
        raise CheckFailed(f"{path.name} has no video stream", data={"ok": False, "path": str(path)})
    s = streams[0]
    fmt = data.get("format") or {}
    pix = s.get("pix_fmt") or ""
    frames = s.get("nb_read_frames") or s.get("nb_frames")
    dur = s.get("duration") or fmt.get("duration")
    return {
        "codec": s.get("codec_name"), "width": s.get("width"), "height": s.get("height"),
        "pix_fmt": pix, "alpha": pix.startswith(ALPHA_FMTS),
        "r_frame_rate": s.get("r_frame_rate"), "avg_frame_rate": s.get("avg_frame_rate"),
        "frames": int(frames) if frames not in (None, "N/A") else None,
        "duration_s": float(dur) if dur not in (None, "N/A") else None,
        "container": fmt.get("format_name"),
    }


def _frames(path: Path, plane: str):
    vf = f"scale={GRID_W}:{GRID_H}:flags=area,format=gray"
    if plane == "alpha":
        vf = "alphaextract," + vf
    cmd = [_need("ffmpeg"), "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    size = GRID_W * GRID_H
    try:
        while True:
            buf = proc.stdout.read(size)
            if not buf or len(buf) < size:
                break
            yield buf
    finally:
        proc.stdout.close()
        err = proc.stderr.read().decode(errors="replace")
        proc.stderr.close()
        rc = proc.wait()
        if rc != 0:
            raise CheckFailed(f"ffmpeg could not decode {path.name} ({plane}): {err.strip()[:300]}")


def _diff_mask(a: bytes, b: bytes, thr: int) -> set:
    return {i for i, (x, y) in enumerate(zip(a, b)) if abs(x - y) >= thr}


def _same(a: bytes, b: bytes, idx, thr: int) -> set:
    return {i for i in idx if abs(a[i] - b[i]) <= thr}


def _near(idx: set, others: set, radius: int) -> set:
    """Blocks of idx with at least one block of others within `radius` cells (2D prefix sums)."""
    if not others or not idx:
        return set()
    W = GRID_W + 1
    pre = [0] * (W * (GRID_H + 1))
    for y in range(GRID_H):
        run = 0
        for x in range(GRID_W):
            run += 1 if (y * GRID_W + x) in others else 0
            pre[(y + 1) * W + (x + 1)] = pre[y * W + (x + 1)] + run
    out = set()
    for i in idx:
        y, x = divmod(i, GRID_W)
        y0, y1 = max(0, y - radius), min(GRID_H, y + radius + 1)
        x0, x1 = max(0, x - radius), min(GRID_W, x + radius + 1)
        if pre[y1 * W + x1] - pre[y0 * W + x1] - pre[y1 * W + x0] + pre[y0 * W + x0] > 0:
            out.add(i)
    return out


def _components(idx: set) -> list[set]:
    idx = set(idx)
    comps = []
    while idx:
        seed = idx.pop()
        comp, stack = {seed}, [seed]
        while stack:
            i = stack.pop()
            y, x = divmod(i, GRID_W)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    j = yy * GRID_W + xx
                    if 0 <= yy < GRID_H and 0 <= xx < GRID_W and j in idx:
                        idx.discard(j)
                        comp.add(j)
                        stack.append(j)
        comps.append(comp)
    return comps


def scan_flashes(path: Path, *, alpha: bool = False) -> dict:
    """Find content visible for only one or two frames. Returns frames scanned and findings."""
    planes = ["luma"] + (["alpha"] if alpha else [])
    findings = []
    counts = {}
    for plane in planes:
        win: list[bytes] = []
        n = 0
        for buf in _frames(path, plane):
            win.append(buf)
            if len(win) > 4:
                win.pop(0)
            n += 1
            # With frames f[-1]=prev ... evaluate a flash that started at index n-3 (L=1) or n-4 (L=2)
            if len(win) >= 3:
                prev, cur, nxt = win[-3], win[-2], win[-1]
                findings += _check(prev, [cur], nxt, n - 2, plane, 1)
            if len(win) >= 4:
                prev, c1, c2, nxt = win[-4], win[-3], win[-2], win[-1]
                findings += _check(prev, [c1, c2], nxt, n - 3, plane, 2)
        counts[plane] = n
    # A 2-frame flash also trips neither 1-frame test, but keep only one finding per start frame.
    seen, unique = set(), []
    for f in sorted(findings, key=lambda f: (f["frame"], -f["length"], f["plane"])):
        k = (f["frame"], f["plane"])
        if k in seen:
            continue
        seen.add(k)
        unique.append(f)
    return {"frames_scanned": counts.get("luma", 0), "planes": planes, "findings": unique,
            "method": {"grid": f"{GRID_W}x{GRID_H}", "change": CHANGE, "return": RETURN, "near": NEAR}}


def _check(prev: bytes, held: list[bytes], nxt: bytes, start: int, plane: str, length: int) -> list[dict]:
    appeared = _diff_mask(prev, held[0], CHANGE)
    for h in held[1:]:
        appeared &= _diff_mask(prev, h, CHANGE)
    if not appeared:
        return []
    gone = _same(prev, nxt, appeared, RETURN)
    if not gone:
        return []
    # Context check: a lasting change (the frame after differs from the frame before) close to
    # the vanished region means it was part of motion or a transition, not an isolated flash.
    moved_to = _diff_mask(prev, nxt, CHANGE)
    out = []
    for comp in _components(gone):
        near = _near(comp, moved_to, NEAR)
        if len(near) * 2 >= len(comp):
            continue
        ys = [i // GRID_W for i in comp]
        xs = [i % GRID_W for i in comp]
        out.append({
            "frame": start, "length": length, "plane": plane, "blocks": len(comp),
            "area_pct": round(100 * len(comp) / (GRID_W * GRID_H), 2),
            "box_pct": {"x0": round(100 * min(xs) / GRID_W, 1), "y0": round(100 * min(ys) / GRID_H, 1),
                        "x1": round(100 * (max(xs) + 1) / GRID_W, 1), "y1": round(100 * (max(ys) + 1) / GRID_H, 1)},
        })
    return out


def expected_for(ctx: Context, item: str, path: Path) -> dict:
    """The spec a render is held to: project render settings, then per-scene duration."""
    settings = ctx.project_settings()
    render = settings.get("render") or {}
    scene = (settings.get("scenes") or {}).get(item) or {}
    exp = {"fps": ctx.fps, "fps_source": ctx.fps_source}
    if render.get("fps"):
        exp["fps"], exp["fps_source"] = fpsmod.parse_rate(render["fps"]), "aem.project.json render.fps"
    for k in ("width", "height"):
        v = scene.get(k, render.get(k))
        if v is not None:
            exp[k] = int(v)
    alpha = scene.get("alpha")
    if alpha is None:
        alpha_ext = [e.lower() for e in render.get("alpha_extensions", [])]
        if alpha_ext:
            alpha = path.suffix.lower() in alpha_ext
        elif "alpha" in render:
            alpha = bool(render["alpha"])
    if alpha is not None:
        exp["alpha"] = bool(alpha)
    if scene.get("frames") is not None:
        exp["frames"], exp["frames_source"] = int(scene["frames"]), "aem.project.json scenes"
    elif scene.get("duration_s") is not None and exp["fps"]:
        exp["frames"] = fpsmod.seconds_to_frame(scene["duration_s"], exp["fps"])
        exp["frames_source"] = "aem.project.json scenes duration_s"
    else:
        src = approvals.scene_source(ctx, item)
        if src and src.suffix == ".html" and exp["fps"]:
            import re
            m = re.search(r'data-duration="([0-9.]+)"', src.read_text(encoding="utf-8", errors="replace"))
            if m:
                exp["frames"] = fpsmod.seconds_to_frame(m.group(1), exp["fps"])
                exp["frames_source"] = f"{rel_to(src, ctx.project_dir)} data-duration {m.group(1)}s"
    return exp


def check_render(ctx: Context, path: str, *, item: str | None = None, record: bool = True) -> dict:
    p = approvals.resolve_path(ctx, path)
    if not p.is_file():
        raise CheckFailed(f"render not found: {p}", data={"ok": False, "path": str(p)})
    it = approvals.item_for(ctx, p, item)
    info = probe(p)
    exp = expected_for(ctx, it, p)
    checks = []

    def add(name, ok, expected, actual, detail=None):
        checks.append({"check": name, "ok": ok, "expected": expected, "actual": actual,
                       **({"detail": detail} if detail else {})})

    for dim in ("width", "height"):
        if dim in exp:
            add(dim, info[dim] == exp[dim], exp[dim], info[dim])
        else:
            add(dim, None, None, info[dim], "not checked: no render.width/height in aem.project.json")
    fps = exp.get("fps")
    actual_fps = None
    try:
        actual_fps = fpsmod.parse_rate(info["r_frame_rate"])
    except AemError:
        pass
    if fps:
        add("fps", actual_fps == fps, fpsmod.rate_str(fps), info["r_frame_rate"], exp.get("fps_source"))
        if info["avg_frame_rate"] and info["avg_frame_rate"] != "0/0":
            avg = fpsmod.parse_rate(info["avg_frame_rate"])
            if avg != actual_fps:
                add("constant frame rate", False, info["r_frame_rate"], info["avg_frame_rate"],
                    "average rate differs from the stream rate: variable frame rate")
    else:
        add("fps", None, None, info["r_frame_rate"], "not checked: project frame rate unknown")
    if "frames" in exp:
        add("frame count", info["frames"] == exp["frames"], exp["frames"], info["frames"], exp.get("frames_source"))
    else:
        add("frame count", None, None, info["frames"], "not checked: no expected duration for this scene")
    if actual_fps and info["frames"] is not None and info["duration_s"] is not None:
        expect_dur = float(Fraction(info["frames"]) / actual_fps)
        ok = abs(info["duration_s"] - expect_dur) <= float(1 / actual_fps) / 2
        add("duration", ok, round(expect_dur, 6), info["duration_s"], "frames ÷ stream fps, within half a frame")
    if "alpha" in exp:
        add("alpha", info["alpha"] == exp["alpha"], exp["alpha"], info["alpha"], info["pix_fmt"])
    else:
        add("alpha", None, None, info["alpha"], f"not checked: {info['pix_fmt']}")

    scan = scan_flashes(p, alpha=info["alpha"])
    if info["frames"] is not None and scan["frames_scanned"] != info["frames"]:
        add("decoded frames", False, info["frames"], scan["frames_scanned"], "ffmpeg decoded a different count than ffprobe")
    fps_for_tc = fps or actual_fps
    for f in scan["findings"]:
        if fps_for_tc:
            f["seconds"] = round(float(fpsmod.frame_to_seconds(f["frame"], fps_for_tc)), 4)
            f["timecode"] = fpsmod.frame_to_timecode(f["frame"], fps_for_tc)
    flash_cfg = ctx.project_settings().get("flash") or {}
    min_area = float(flash_cfg.get("min_area_pct", MIN_AREA_PCT))
    for f in scan["findings"]:
        f["severity"] = "fail" if f["area_pct"] >= min_area else "minor"
    major = [f for f in scan["findings"] if f["severity"] == "fail"]
    add("short flashes (1-2 frames)", not major, 0, len(major),
        f"{len(scan['findings']) - len(major)} minor finding(s) under {min_area}% of the frame listed, not failed; "
        "first and last frame cannot be scanned")

    sha = sha256_file(p)
    failed = [c for c in checks if c["ok"] is False]
    rel = rel_to(p, ctx.project_dir)
    result = {
        "ok": not failed, "result": "pass" if not failed else "fail", "scene": it, "path": rel,
        "render_sha256": sha, "probe": info, "expected": {k: (fpsmod.rate_str(v) if isinstance(v, Fraction) else v)
                                                           for k, v in exp.items()},
        "checks": checks, "flashes": scan["findings"], "flash_scan": {k: scan[k] for k in ("frames_scanned", "planes", "method")},
        "failures": [f"{c['check']}: expected {c['expected']}, got {c['actual']}" for c in failed],
    }
    if record:
        stale = approvals.mark_stale(ctx, it, sha, rel, f"render changed; check-render saw {sha[:12]}…")
        result["stale_marked"] = [{"gate": s["gate"], "render_sha256": s["render_sha256"]} for s in stale]
        note = "pass" if result["ok"] else "fail: " + "; ".join(result["failures"])
        ledger.record(ctx, "render_check", scene=it, note=note, render=rel, render_sha256=sha,
                      result=result["result"], failures=result["failures"] or None,
                      flashes=[{k: f.get(k) for k in ("frame", "length", "plane", "area_pct", "timecode")} for f in scan["findings"]] or None,
                      stale_marked=len(stale) or None, source="aem check-render")
    if failed:
        raise CheckFailed(f"{rel}: " + "; ".join(result["failures"]), data=result)
    return result
