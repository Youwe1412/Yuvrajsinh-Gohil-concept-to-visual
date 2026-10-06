#!/usr/bin/env bash
# The operator's side of the Phase 7 acceptance test, typed into headless Claude Code sessions
# (`claude -p`) with this repository's plugin loaded, exactly as Yuvraj would type them. Each step
# is fixed: this script is not a general way to run operator commands.
#
#   tests/acceptance/operator.sh <use|g1|g4-approve|approve|g6|report|clear> <registry.json>
#
# The agent's side (editing a protected file, rendering, placing) is done by the agent in a live
# session with the plugin loaded, so its guard and sentinel are the ones under test.
set -euo pipefail
STEP="$1"
REG="${2:-}"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
PLUGIN="$HERE/plugin/aavkar-educational-motion-studio"
# The desktop app's newest bundled Claude Code when present (the PATH one can be older), else PATH.
NEWEST="$(ls -1d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1 || true)"
CLAUDE="${CLAUDE:-${NEWEST:-claude}}"

type_cmd() {
  echo "operator> $1"
  "$CLAUDE" -p --plugin-dir "$PLUGIN" "$1" 2>&1 | sed 's/^/  /'
}

case "$STEP" in
  use)        type_cmd "/aem use joel/P1 --registry $REG" ;;
  g1)         type_cmd "/stage G1" ;;
  g4-approve) type_cmd "/stage G4 fd_S01_next-token"; type_cmd "/approve fd_S01_next-token" ;;
  approve)    type_cmd "/approve fd_S01_next-token" ;;
  g6)         type_cmd "/stage G6 fd_S01_next-token" ;;
  report)     type_cmd "/stage end"; type_cmd "/report" ;;
  clear)      type_cmd "/aem use --clear" ;;
  *) echo "unknown step $STEP" >&2; exit 2 ;;
esac
