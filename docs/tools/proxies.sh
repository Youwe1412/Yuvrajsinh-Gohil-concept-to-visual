#!/usr/bin/env bash
# Encode 1080p H.264 proxies of the latest render of every animation moment in docs/showcase/
# into docs/showcase/video/<moment>.mp4 (about 1 MB per 30 s). Full 4K renders stay in the
# project folder. Usage: docs/tools/proxies.sh "<P2 project folder>"
set -euo pipefail
P2="${1:?P2 project folder}"
cd "$(dirname "$0")/../.."
mkdir -p docs/showcase/video
for d in docs/showcase/cc_S*/; do
  n=$(basename "$d")
  src=$(ls "$P2/renders/${n}_v"*.mp4 "$P2/renders/${n}_v"*.mov 2>/dev/null | sort | tail -1 || true)
  [ -n "$src" ] || { echo "no render for $n"; continue; }
  if [ -f "docs/showcase/video/${n}.mp4" ] && [ ! "$src" -nt "docs/showcase/video/${n}.mp4" ]; then echo "$n up to date"; continue; fi
  ffmpeg -v error -y -i "$src" -vf scale=1920:-2 -c:v libx264 -crf 23 -preset fast \
    -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "docs/showcase/video/${n}.mp4"
  echo "$n <- $(basename "$src")"
done
du -sh docs/showcase/video
