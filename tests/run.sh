#!/usr/bin/env bash
# Runs the CLI unit tests and the plugin tests against a sandbox AEM_HOME and registry copy, and
# fails if the operator's ~/.aem or registry/clients.json changed during the run.
#
#   tests/run.sh            both suites
#   tests/run.sh unit       CLI unit tests only
#   tests/run.sh plugin     plugin tests only
set -uo pipefail
WHICH="${1:-all}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ISO="$HERE/tests/isolation.py"
NEWEST="$(ls -1d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1 || true)"
CLAUDE="${CLAUDE:-${NEWEST:-claude}}"

SNAP="$(mktemp)"
python3 "$ISO" snapshot "$SNAP" || exit 2
eval "$(python3 "$ISO" sandbox aem-run-)"
trap 'rm -rf "$SNAP" "$AEM_SANDBOX"' EXIT

status=0
if [ "$WHICH" = all ] || [ "$WHICH" = unit ]; then
  echo "== CLI unit tests"
  (cd "$HERE" && python3 -m unittest discover -s tests -t tests) || status=1
fi
if [ "$WHICH" = all ] || [ "$WHICH" = plugin ]; then
  echo "== plugin tests"
  (cd "$HERE" && "$CLAUDE" plugin test plugin/aavkar-educational-motion-studio) || status=1
fi
echo "== isolation"
python3 "$ISO" check "$SNAP" || status=1
exit $status
