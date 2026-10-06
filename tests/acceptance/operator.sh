#!/usr/bin/env bash
# The operator's side of the Phase 7 acceptance test, typed into headless Claude Code sessions
# (`claude -p`) with this repository's plugin loaded, exactly as Yuvraj would type them. Each step
# is fixed: this script is not a general way to run operator commands.
#
#   tests/acceptance/operator.sh init                    make a sandbox; prints its folder
#   tests/acceptance/operator.sh <step> <sandbox>        step: use|g1|g4-approve|approve|g6|report|clear
#
# Every step runs against the sandbox only: AEM_HOME is <sandbox>/aem-home and the registry is
# <sandbox>/clients.json, a copy of registry/clients.json with every client's folders inside the
# sandbox. Copy the design system and the test project into <sandbox>/<client folder>/ before `use`.
# The script refuses a folder that is not such a sandbox, and fails if ~/.aem or
# registry/clients.json changed while a step ran.
#
# The agent's side (editing a ledger by hand, rendering, placing) is done by an agent session with
# the plugin loaded and the same AEM_HOME, so its observation, sentinel and delivery confirmation are
# the ones under test.
set -euo pipefail
STEP="${1:-}"
SB="${2:-}"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
ISO="$HERE/tests/isolation.py"
PLUGIN="$HERE/plugin/aavkar-educational-motion-studio"
# The desktop app's newest bundled Claude Code when present (the PATH one can be older), else PATH.
NEWEST="$(ls -1d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1 || true)"
CLAUDE="${CLAUDE:-${NEWEST:-claude}}"

if [ "$STEP" = init ]; then
  eval "$(python3 "$ISO" sandbox aem-acceptance-)"
  echo "$AEM_SANDBOX_DIR"
  exit 0
fi
[ -n "$SB" ] || { echo "usage: $0 init | $0 <step> <sandbox>" >&2; exit 2; }
SB="$(cd "$SB" && pwd -P)"
python3 "$ISO" verify "$SB"
export AEM_HOME="$SB/aem-home" AEM_REGISTRY="$SB/clients.json" AEM_SANDBOX=1
# The project comes from the environment of the process (the sandbox registry has the test copy registered
# as P1), as a session started in that folder resolves it. Nothing global is written.
export AEM_PROJECT="${AEM_PROJECT:-joel/P1}"
SNAP="$(mktemp)"
trap 'rm -f "$SNAP"' EXIT
python3 "$ISO" snapshot "$SNAP"

type_cmd() {
  echo "operator> $1"
  "$CLAUDE" -p --plugin-dir "$PLUGIN" "$1" 2>&1 | sed 's/^/  /'
}

case "$STEP" in
  use)        type_cmd "/aem use $AEM_PROJECT" ;;
  g1)         type_cmd "/stage G1" ;;
  g4-approve) type_cmd "/stage G4 fd_S01_next-token"; type_cmd "/approve fd_S01_next-token" ;;
  approve)    type_cmd "/approve fd_S01_next-token" ;;
  g6)         type_cmd "/stage G6 fd_S01_next-token" ;;
  report)     type_cmd "/stage end"; type_cmd "/report" ;;
  clear)      type_cmd "/aem use --clear" ;;   # drops that headless session's pin; nothing global to clear
  *) echo "unknown step $STEP" >&2; exit 2 ;;
esac

python3 "$ISO" check "$SNAP"
