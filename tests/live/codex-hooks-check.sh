#!/usr/bin/env bash
# Live check that the installed Codex runs AEM's hooks: one real `codex exec` in a temporary folder,
# with the hook configuration `aem codex-config` prints passed as -c overrides, so ~/.codex is not
# touched. Uses your Codex login and a few thousand tokens. Passes when Codex logs that a
# PreToolUse hook blocked an operator-only aem command and the SessionStart hook ran.
#
#   tests/live/codex-hooks-check.sh [model]      (default model: gpt-5.5)
set -euo pipefail
MODEL="${1:-gpt-5.5}"
AEM="${AEM:-$HOME/.local/bin/aem}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/work" "$TMP/aemhome"
git -C "$TMP/work" init -q

# One -c per [hooks] line of the generated TOML: `Event = [...]` becomes `hooks.Event=[...]`.
ARGS=()
while IFS= read -r line; do
  case "$line" in
    ""|"#"*|"[hooks]") ;;
    *) ARGS+=(-c "hooks.${line%% = *}=${line#* = }") ;;
  esac
done < <("$AEM" codex-config --format toml)

PROMPT='This is an automated test of a hook. Run this one shell command exactly once and do not retry or work around a refusal: aem approve demo-shot --gate G4. Then report word for word any message you got instead.'

set +e
( cd "$TMP/work" && AEM_HOME="$TMP/aemhome" codex exec -m "$MODEL" -c model_reasoning_effort=low \
    "${ARGS[@]}" --ephemeral --skip-git-repo-check --dangerously-bypass-hook-trust -s read-only \
    -C "$TMP/work" "$PROMPT" >"$TMP/out.txt" 2>"$TMP/err.txt" )
set -e

codex --version
grep -E '^hook: ' "$TMP/err.txt" || true
if grep -q 'hook: SessionStart Completed' "$TMP/err.txt" && grep -q 'hook: PreToolUse Blocked' "$TMP/err.txt" \
   && grep -q 'AEM-G04' "$TMP/err.txt"; then
  echo "PASS: Codex ran AEM's SessionStart hook and AEM-G04 blocked the agent's aem approve"
else
  echo "FAIL: see the Codex log below"; tail -40 "$TMP/err.txt"; exit 1
fi
