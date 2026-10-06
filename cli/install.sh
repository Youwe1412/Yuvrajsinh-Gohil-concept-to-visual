#!/bin/bash
# Installs the `aem` command by linking cli/bin/aem into a folder on PATH.
# Usage: cli/install.sh [target-dir]   (default: ~/.local/bin)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/.local/bin}"
mkdir -p "$TARGET"
if [ -e "$TARGET/aem" ] && [ "$(readlink "$TARGET/aem" || true)" != "$HERE/bin/aem" ]; then
  echo "refusing: $TARGET/aem exists and is not this AEM's launcher" >&2
  exit 1
fi
chmod +x "$HERE/bin/aem"
ln -sfn "$HERE/bin/aem" "$TARGET/aem"
echo "Linked $TARGET/aem -> $HERE/bin/aem"
case ":$PATH:" in *":$TARGET:"*) ;; *) echo "Note: $TARGET is not on PATH; add it to your shell profile." ;; esac
command -v python3 >/dev/null || echo "Note: python3 not found on PATH."
command -v ffprobe >/dev/null && command -v ffmpeg >/dev/null || echo "Note: ffmpeg/ffprobe not found; check-render needs them."
