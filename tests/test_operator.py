"""Phase 2 (0.8.0): operator-only commands are refused by the CLI itself, not by matching shell text.

Regressions from 6 October 2026: the old guard matched the text of a command, so a commit message or a
heredoc that mentioned `aem approve` was denied (test_guard covers those), while the same command spelled
another way (a script, a wrapper, python -m) was not the guard's to see. Now the command refuses at its
entry, whatever the spelling, unless the operator is shown to be running it.
"""
import json
import os
import pty
import shlex
import subprocess
import sys
import time
import unittest
from pathlib import Path

from helpers import AEM, REPO, WorldCase
from aem import operator

OPERATOR_COMMANDS = [
    ("use", "acme/P1"),
    ("stage", "start", "G1"),
    ("stage", "auto", "prompt"),
    ("approve", "x"),
    ("reject", "x", "--reason", "r"),
    ("client-said", "--scope", "video", "--source", "email"),
    ("allow", "AEM-G02", "--reason", "r"),
    ("new-client", "beta", "--name", "Beta", "--design-system", "/nonexistent/ds", "--projects-root", "/nonexistent"),
    ("inbox", "accept", "x", "--ruling", "keep"),
    ("inbox", "dismiss", "x", "--reason", "r"),
]


class Refused(WorldCase):
    def assertRefused(self, code, d, why=None):
        self.assertEqual(code, 2, d)
        self.assertTrue(d.get("operator_only"), d)
        self.assertIn("operator's command", d["error"])
        self.assertIn("ask the operator", d["hint"])
        if why:
            self.assertIn(why, d["error"])

    def test_every_operator_command_is_refused_from_a_non_terminal_without_a_nonce(self):
        for args in OPERATOR_COMMANDS:
            code, d = self.w.run(*args, stdin="words\n", operator=False)
            self.assertRefused(code, d, "not a terminal")
        self.assertEqual(self.w.events(), [])  # and nothing was written
        self.assertEqual(self.w.approvals(), [])

    def test_approve_x_from_a_non_tty_process_is_refused(self):
        code, d = self.w.run("approve", "x", operator=False)
        self.assertRefused(code, d, "not a terminal")
        self.assertFalse((self.w.project / "approvals.jsonl").exists())

    def test_through_a_shell_script(self):
        script = self.w.tmp / "do-it.sh"
        script.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(AEM))} approve x --json\n")
        script.chmod(0o755)
        p = subprocess.run(["sh", str(script)], capture_output=True, text=True, env=self.w.env, cwd=str(self.w.project))
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue(json.loads(p.stdout)["operator_only"])

    def test_through_python_dash_m(self):
        env = {**self.w.env, "PYTHONPATH": str(REPO / "cli")}
        p = subprocess.run([sys.executable, "-m", "aem", "approve", "x", "--json"], capture_output=True, text=True,
                           env=env, cwd=str(self.w.project))
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue(json.loads(p.stdout)["operator_only"])

    def test_through_a_wrapper_under_another_name(self):
        link = self.w.tmp / "totally-not-the-tool"
        link.symlink_to(AEM)
        p = subprocess.run([sys.executable, str(link), "stage", "start", "G1", "--json"], capture_output=True, text=True,
                           env=self.w.env, cwd=str(self.w.project))
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue(json.loads(p.stdout)["operator_only"])

    def test_through_a_script_that_imports_the_library_directly(self):
        code = ("import sys, argparse; sys.path.insert(0, %r)\n"
                "from aem import ledger, registry\n"
                "ledger.stage(registry.context(argparse.Namespace()), 'start', ['G1'])\n" % str(REPO / "cli"))
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=self.w.env, cwd=str(self.w.project))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("may only run through an `aem` command that passed the operator check", p.stderr)
        self.assertEqual(self.w.events(), [])

    def test_open_commands_need_no_operator(self):
        for args, stdin in ((("status",), None), (("context",), None), (("report", "--no-write"), None),
                            (("check-approval", "renders/none.mp4"), None), (("inbox",), None),
                            (("guard",), json.dumps({"tool": "Read", "input": {"file_path": str(self.w.project / "a")}}))):
            code, d = self.w.run(*args, stdin=stdin, operator=False)
            self.assertNotIn("operator_only", d, args)

    def test_a_refusal_does_not_leak_or_consume_anything_else(self):
        nonce = "feedface" * 8
        code, d = self.w.run("approve", "x", operator=False, env={"AEM_OPERATOR_NONCE": nonce})
        self.assertEqual(code, 2)
        self.assertNotIn(nonce, json.dumps(d))
        self.assertIn("unknown or already used", d["error"])


class Nonce(WorldCase):
    def run_with(self, nonce, *args):
        return self.w.run(*args, operator=False, env={"AEM_OPERATOR_NONCE": nonce})

    def test_a_valid_nonce_works_once_and_not_twice(self):
        n = self.w.make_nonce()
        code, d = self.run_with(n, "stage", "start", "G1")
        self.assertEqual(code, 0, d)
        self.assertEqual(self.w.events()[-1]["event"], "start")
        code, d = self.run_with(n, "stage", "start", "G2")
        self.assertEqual(code, 2)
        self.assertTrue(d["operator_only"])
        self.assertIn("unknown or already used", d["error"])
        self.assertEqual([e["gate"] for e in self.w.events()], ["G1"])  # the second did nothing

    def test_an_expired_nonce_is_refused_and_removed(self):
        n = self.w.make_nonce(ttl_s=-1)
        code, d = self.run_with(n, "stage", "start", "G1")
        self.assertEqual(code, 2)
        self.assertIn("expired", d["error"])
        self.assertEqual(self.w.events(), [])
        self.assertEqual(list((self.w.home / "nonces").iterdir()), [])

    def test_the_default_life_is_sixty_seconds(self):
        self.assertEqual(operator.NONCE_TTL_S, 60)
        n = self.w.make_nonce()
        rec = json.loads((self.w.home / "nonces" / operator.nonce_hash(n)).read_text())
        self.assertAlmostEqual(rec["expires_at"] - time.time(), 60, delta=5)

    def test_only_the_hash_is_on_disk_and_the_nonce_is_never_in_output_or_the_ledger(self):
        n = self.w.make_nonce()
        files = list((self.w.home / "nonces").iterdir())
        self.assertEqual([f.name for f in files], [operator.nonce_hash(n)])
        self.assertNotIn(n, files[0].read_text())
        code, d = self.run_with(n, "stage", "start", "G1")
        self.assertEqual(code, 0)
        self.assertNotIn(n, json.dumps(d))
        self.assertNotIn(n, (self.w.project / "events.jsonl").read_text())
        for f in self.w.tmp.rglob("*"):
            if f.is_file() and f.stat().st_size < 1_000_000:
                self.assertNotIn(n.encode(), f.read_bytes(), str(f))

    def test_a_used_nonce_is_gone_from_disk(self):
        n = self.w.make_nonce()
        self.run_with(n, "stage", "start", "G1")
        self.assertFalse((self.w.home / "nonces" / operator.nonce_hash(n)).exists())

    def test_the_nonce_variable_is_removed_from_the_process_so_children_do_not_inherit_it(self):
        n = self.w.make_nonce()
        with self.w.environ():
            os.environ[operator.NONCE_VAR] = n
            try:
                self.assertIsNone(operator.nonce_problem())
                self.assertNotIn(operator.NONCE_VAR, os.environ)
            finally:
                os.environ.pop(operator.NONCE_VAR, None)

    def test_a_nonce_in_another_aem_home_is_not_valid(self):
        n = self.w.make_nonce()
        other = self.w.tmp / "other-home"
        code, d = self.w.run("stage", "start", "G1", operator=False,
                             env={"AEM_OPERATOR_NONCE": n, "AEM_HOME": str(other)})
        self.assertEqual(code, 2)

    def test_expired_nonces_are_cleaned_up_when_any_nonce_is_checked(self):
        old = self.w.make_nonce(ttl_s=-5)
        fresh = self.w.make_nonce()
        self.run_with(fresh, "stage", "start", "G1")
        self.assertFalse((self.w.home / "nonces" / operator.nonce_hash(old)).exists())


class Terminal(WorldCase):
    """The operator's own terminal: a pseudo-terminal that is the controlling terminal, no agent markers."""

    def test_a_real_terminal_runs_an_operator_command(self):
        code, out = self.w.run_tty("stage", "start", "G1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.w.events()[-1]["event"], "start")

    def test_client_said_reads_the_quote_typed_into_the_terminal(self):
        code, out = self.w.run_tty("client-said", "--scope", "video", "--source", "Frame.io",
                                   keyboard="Keep it calm.\n\x04")
        self.assertEqual(code, 0, out)
        self.assertIn("> Keep it calm.", (self.w.ds / "acme-decisions.md").read_text())

    def test_a_terminal_under_an_agent_is_refused_even_though_it_has_a_tty(self):
        # An agent's shell can allocate a pty (script, Python's pty): stdin and stdout are then a terminal and
        # /dev/tty opens. What it cannot hide is what it inherited: the agent's markers.
        for marker in operator.AGENT_MARKERS:
            code, out = self.w.run_tty("stage", "start", "G1", env={marker: "1"})
            self.assertEqual(code, 2, (marker, out))
            self.assertIn(f"{marker} is set", out)
        self.assertEqual(self.w.events(), [])

    def test_a_clean_terminal_is_not_affected_by_the_markers_of_the_agent_running_this_suite(self):
        # This suite usually runs under Claude Code, so its own environment has markers; run_tty removes
        # them, as the operator's own terminal never had them.
        code, out = self.w.run_tty("stage", "start", "G1")
        self.assertEqual(code, 0, out)

    def test_a_terminal_on_stdin_with_a_pipe_on_stdout_is_not_the_operators_terminal(self):
        # The agent's shell captures output through pipes, so stdout is not a terminal.
        master, slave = pty.openpty()
        try:
            p = subprocess.run([sys.executable, str(AEM), "stage", "start", "G1", "--json"], stdin=slave,
                               capture_output=True, text=True, env=self.w.env, cwd=str(self.w.project))
        finally:
            os.close(master)
            os.close(slave)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue(json.loads(p.stdout)["operator_only"])


if __name__ == "__main__":
    unittest.main()
