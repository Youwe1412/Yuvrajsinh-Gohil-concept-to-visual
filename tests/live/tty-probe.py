#!/usr/bin/env python3
"""What does a process see of a terminal? Run it from where you want to know: your own Terminal, a Claude
Code session (type `! python3 tests/live/tty-probe.py claude-cli`, or have the agent run it), a Codex session.

    python3 tests/live/tty-probe.py [label]

It prints one JSON object: whether stdin/stdout/stderr are terminals, whether /dev/tty can be opened, and the
names (not values) of the environment variables that mark an AI agent. `aem`'s operator check
(cli/aem/operator.py) looks at exactly these. Results on 6 October 2026 are in docs/CLI.md.
"""
import json
import os
import sys

record = {
    "who": sys.argv[1] if len(sys.argv) > 1 else "?",
    "stdin_tty": sys.stdin.isatty(),
    "stdout_tty": sys.stdout.isatty(),
    "stderr_tty": sys.stderr.isatty(),
}
try:
    os.close(os.open("/dev/tty", os.O_RDWR))
    record["dev_tty"] = "opens"
except OSError as exc:
    record["dev_tty"] = f"fails: {exc.strerror}"
record["agent_markers"] = sorted(k for k in os.environ if k.startswith(("CODEX", "CLAUDE", "AI_AGENT", "ANTHROPIC")))
print(json.dumps(record))
