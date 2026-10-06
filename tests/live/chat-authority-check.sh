#!/usr/bin/env bash
# Live check of operator authority from chat (0.9.0), with the INSTALLED plugin in a headless Claude Code
# session (`claude -p`, whose prompts come from the SDK host, an operator origin), against a sandbox only.
#
#   tests/live/chat-authority-check.sh
#
# It builds a sandbox copy of Joel's registry entry with an empty design system and a P2 project inside the
# sandbox, asks the agent to run `aem stage start G2` and to read events.jsonl with the shell (AEM-G01 would
# deny that in an autonomous turn), then checks events.jsonl: the operator_prompt, the stage start recorded
# via chat with the prompt's id, the guard's allowed_by_operator_prompt, and no authority left on disk.
# It fails if ~/.aem or registry/clients.json changed. It makes one model call per prompt.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
ISO="$HERE/tests/isolation.py"
NEWEST="$(ls -1d "$HOME/Library/Application Support/Claude/claude-code"/*/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1 || true)"
CLAUDE="${CLAUDE:-${NEWEST:-claude}}"

SNAP="$(mktemp)"
python3 "$ISO" snapshot "$SNAP"
eval "$(python3 "$ISO" sandbox aem-chat-live-)"
trap 'rm -rf "$SNAP" "$AEM_SANDBOX_DIR"' EXIT

P2="$(python3 - <<'EOF'
import json, os
from pathlib import Path
reg = json.loads(Path(os.environ["AEM_REGISTRY"]).read_text())
c = next(c for c in reg["clients"] if c["id"] == "joel")
ds, root = Path(c["design_system"]), Path(c["projects_root"])
(ds / "critic").mkdir(parents=True)
(ds / "joel-decisions.md").write_text("# Joel's decisions\n\n---\n")
(ds / "rules.md").write_text("# Rules\n")
(ds / "critic" / "labelled-cases.jsonl").write_text(json.dumps({"_comment": "test", "fields": {}}) + "\n")
p2 = root / c["projects"]["P2"]["dir"]
p2.mkdir(parents=True)
(p2 / "aem.project.json").write_text(json.dumps({"fps": "25/1"}))
print(p2)
EOF
)"
cd "$P2"
echo "sandbox project: $P2"
echo "claude: $("$CLAUDE" --version)"

ask() {
  echo "operator> $1"
  "$CLAUDE" -p "$1" --allowedTools=Bash 2>&1 | sed 's/^/  /'
}

ask 'Start G2 for this project: run exactly `aem stage start G2` in the shell, then run `cat events.jsonl | tail -n 3` and tell me what was recorded.'

python3 - "$P2" "$AEM_HOME" <<'EOF'
import json, sys
from pathlib import Path
p2, home = Path(sys.argv[1]), Path(sys.argv[2])
ev = [json.loads(l) for l in (p2 / "events.jsonl").read_text().splitlines() if l.strip()]
names = [e["event"] for e in ev]
print("events:", names)
prompt = [e for e in ev if e["event"] == "operator_prompt"]
start = [e for e in ev if e["event"] == "start" and e.get("gate") == "G2"]
allowed = [e for e in ev if e["event"] == "allowed_by_operator_prompt"]
ok = True
def check(cond, what):
    global ok
    print(("PASS " if cond else "FAIL ") + what)
    ok = ok and cond
check(len(prompt) == 1 and prompt[0].get("origin") == "sdk" and "Start G2" in prompt[0].get("prompt_text", ""),
      "operator_prompt recorded with the exact prompt (origin sdk)")
check(len(start) == 1 and start[0].get("via") == "chat" and start[0].get("prompt_id") == (prompt[0]["prompt_id"] if prompt else None),
      "G2 start recorded via chat with the prompt's id")
check(any(a.get("rule") == "AEM-G01" for a in allowed), "the shell read of events.jsonl was allowed and logged (AEM-G01)")
left = [f for f in (home / "nonces").iterdir() if not f.name.endswith(".uses")] if (home / "nonces").exists() else []
turns = [f for f in left if json.loads(f.read_text()).get("kind") == "turn"]
check(turns == [], "no turn authority left on disk after the turn ended")
sys.exit(0 if ok else 1)
EOF
python3 "$ISO" check "$SNAP"
