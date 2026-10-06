#!/usr/bin/env python3
"""Acceptance-test stand-in for a placement step: writes a minimal FCPXML that lists the given
renders as assets on a 24000/1001 timeline. It is not Joel's placement tool (that follows the
skill's references/fcpxml-delivery.md); it only gives AEM-G05 a real command to judge.

    python3 bin/place.py --fcpxml out/placement.fcpxml renders/<master>.mp4 [...]
"""
import argparse
import subprocess
from pathlib import Path
from urllib.parse import quote


def frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                          "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcpxml", required=True)
    ap.add_argument("renders", nargs="+")
    a = ap.parse_args()
    assets, clips, offset = [], [], 0
    for i, r in enumerate(a.renders, start=1):
        p = Path(r).resolve()
        n = frames(p)
        assets.append(f'    <asset id="r{i}" name="{p.stem}" start="0s" duration="{n * 1001}/24000s" hasVideo="1" '
                      f'format="f1"><media-rep kind="original-media" src="file://{quote(str(p))}"/></asset>')
        clips.append(f'          <asset-clip ref="r{i}" offset="{offset * 1001}/24000s" duration="{n * 1001}/24000s" name="{p.stem}"/>')
        offset += n
    xml = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE fcpxml>", '<fcpxml version="1.11">', "  <resources>",
        '    <format id="f1" frameDuration="1001/24000s" width="3840" height="2160"/>', *assets, "  </resources>",
        '  <library><event name="AEM acceptance"><project name="placement">',
        f'    <sequence format="f1" duration="{offset * 1001}/24000s"><spine>', *clips, "    </spine></sequence>",
        "  </project></event></library>", "</fcpxml>", ""])
    out = Path(a.fcpxml)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    print(f"wrote {out} with {len(a.renders)} render(s), {offset} frames")


if __name__ == "__main__":
    main()
