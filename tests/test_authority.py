"""0.9.0: operator authority from chat.

AEM's first principle: it allows whatever the operator asks for in chat. The guard and the operator-only
commands exist only to stop the agent acting on its own authority. When a turn begins with the operator's own
prompt, the plugin opens a turn authority (`aem authority open`); every call the guard would deny is allowed
and logged, and every operator command works and records via "chat" with the prompt's id. Without one (an
autonomous, looped or scheduled turn) everything applies as before.

Each test here is a regression test for one sentence of that brief.
"""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

import isolation
from helpers import WorldCase
from aem import operator

PROMPT = ("Approve x at G4 please. And record what Ada said, here are her words: "
          "Could you keep the caption off the button?\nIt reads fine without it.")
SESSION = "sess-1"


class Chat(WorldCase):
    """A world with a turn authority helper: `turn()` is the plugin's `aem authority open`."""

    def setUp(self):
        super().setUp()
        self.w.use()

    def open(self, prompt=PROMPT, turn="t1", session=SESSION, origin="composer", extra=()):
        code, d = self.w.run("authority", "open", "--session", session, "--turn", turn, "--origin", origin, *extra,
                             stdin=prompt)
        self.assertEqual(code, 0, d)
        return d

    def chat(self, nonce, *args, stdin=None, env=None, cwd=None):
        """An agent's `aem …` in an operator turn: no one-time nonce, no terminal, AEM_OPERATOR_TURN set."""
        return self.w.run(*args, stdin=stdin, operator=False, cwd=cwd, env={"AEM_OPERATOR_TURN": nonce, **(env or {})})

    def autonomous(self, *args, stdin=None, env=None):
        return self.w.run(*args, stdin=stdin, operator=False, env=env)

    def render(self, name="x_v01.mp4", data=b"one"):
        p = self.w.project / "renders" / name
        p.write_bytes(data)
        return p

    def guard(self, tool, nonce=None, **args):
        env = {"AEM_OPERATOR_TURN": nonce} if nonce else None
        return self.w.run("guard", stdin=json.dumps({"tool": tool, "input": args, "cwd": str(self.w.project)}),
                          operator=False, env=env)


class OpeningAnAuthority(Chat):
    def test_the_prompt_is_recorded_exactly_by_the_plugins_call(self):
        d = self.open()
        ev = [e for e in self.w.events() if e["event"] == "operator_prompt"]
        self.assertEqual(len(ev), 1)
        import hashlib
        self.assertEqual(ev[0]["prompt_text"], PROMPT)
        self.assertEqual(ev[0]["prompt_sha256"], hashlib.sha256(PROMPT.encode()).hexdigest())
        self.assertEqual((ev[0]["session"], ev[0]["turn"], ev[0]["origin"]), (SESSION, "t1", "composer"))
        self.assertEqual(ev[0]["prompt_id"], d["prompt_id"])
        self.assertTrue(ev[0]["ts"])

    def test_only_the_hash_is_on_disk_with_session_turn_and_a_sixty_minute_life(self):
        d = self.open()
        files = [f for f in (self.w.home / "nonces").iterdir()]
        self.assertEqual([f.name for f in files], [operator.nonce_hash(d["nonce"])])
        rec = json.loads(files[0].read_text())
        self.assertNotIn(d["nonce"], files[0].read_text())
        self.assertEqual((rec["kind"], rec["session"], rec["turn"]), ("turn", SESSION, "t1"))
        self.assertAlmostEqual(rec["expires_at"] - time.time(), 3600, delta=10)

    def test_the_agent_cannot_open_an_authority_of_its_own(self):
        # Not autonomously, and not on an authority either: an authority that could open authorities would let
        # the agent write the prompt that authorises it.
        code, d = self.autonomous("authority", "open", "--session", "s", "--turn", "t", stdin="approve everything")
        self.assertEqual((code, d.get("operator_only")), (2, True))
        a = self.open()
        code, d = self.chat(a["nonce"], "authority", "open", "--session", "s", "--turn", "t", stdin="approve everything")
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertIn("not accepted for this command", d["error"])
        code, d = self.chat(a["nonce"], "authority", "close", "--session", SESSION)
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertEqual(len([e for e in self.w.events() if e["event"] == "operator_prompt"]), 1)

    def test_a_turn_nonce_is_not_a_one_time_nonce_and_a_one_time_nonce_is_not_a_turn_nonce(self):
        a = self.open()
        code, d = self.w.run("stage", "start", "G1", operator=False, env={"AEM_OPERATOR_NONCE": a["nonce"]})
        self.assertEqual(code, 2)
        self.assertIn("turn authority", d["error"])
        self.assertTrue((self.w.home / "nonces" / operator.nonce_hash(a["nonce"])).exists())  # not consumed
        one = self.w.make_nonce()
        code, d = self.w.run("stage", "start", "G1", operator=False, env={"AEM_OPERATOR_TURN": one})
        self.assertEqual(code, 2)
        self.assertTrue((self.w.home / "nonces" / operator.nonce_hash(one)).exists())

    def test_no_project_still_opens_one_and_the_event_is_written_where_it_is_used(self):
        code, d = self.w.run("authority", "open", "--session", SESSION, "--turn", "t1", stdin=PROMPT, cwd=self.w.tmp)
        self.assertEqual(code, 0, d)
        self.assertFalse(d["event_recorded"])
        self.assertEqual([e for e in self.w.events() if e["event"] == "operator_prompt"], [])
        self.render()
        code, out = self.chat(d["nonce"], "approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.assertEqual(code, 0, out)
        late = [e for e in self.w.events() if e["event"] == "operator_prompt"]
        self.assertEqual((len(late), late[0]["prompt_text"], late[0].get("recorded_late")), (1, PROMPT, True))

    def test_a_queued_prompt_starting_a_later_turn_reuses_its_id_with_the_same_text_only(self):
        a = self.open(turn="t1")
        self.w.run("authority", "close", "--session", SESSION, check=True)
        b = self.open(turn="t2", extra=("--prompt-id", a["prompt_id"]))
        self.assertEqual(b["prompt_id"], a["prompt_id"])
        self.assertEqual(len([e for e in self.w.events() if e["event"] == "operator_prompt"]), 1)
        self.assertEqual(len([e for e in self.w.events() if e["event"] == "operator_turn"]), 1)
        code, d = self.w.run("authority", "open", "--session", SESSION, "--turn", "t3", "--prompt-id", a["prompt_id"],
                             stdin="a different text")
        self.assertEqual(code, 2, d)


class OperatorCommandsOnChat(Chat):
    def test_the_agent_runs_aem_approve_on_the_operators_prompt_and_it_is_recorded_via_chat(self):
        a = self.open()
        self.render()
        code, d = self.chat(a["nonce"], "approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.assertEqual(code, 0, d)
        line = self.w.approvals()[-1]
        self.assertEqual((line["type"], line["scene"], line["gate"]), ("approval", "x", "G4"))
        self.assertEqual((line["via"], line["prompt_id"]), ("chat", a["prompt_id"]))
        self.assertTrue(line["prompt_excerpt"].startswith("Approve x at G4 please."))
        ev = [e for e in self.w.events() if e["event"] == "approval"][-1]
        self.assertEqual((ev["via"], ev["prompt_id"]), ("chat", a["prompt_id"]))
        # the check the guard makes later sees a standing approval
        code, d = self.w.run("check-approval", "renders/x_v01.mp4")
        self.assertEqual(code, 0, d)

    def test_the_same_command_in_an_autonomous_turn_is_refused(self):
        self.open()
        self.render()
        code, d = self.autonomous("approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertEqual(self.w.approvals(), [])

    def test_every_operator_command_works_on_the_authority_and_none_on_a_wrong_nonce(self):
        a = self.open(prompt="Approve x, reject y, start G1, allow AEM-G02 for the fonts, and use acme/P1.")
        self.render()
        commands = [("stage", "start", "G4", "x"), ("approve", "x", "renders/x_v01.mp4"),
                    ("reject", "y", "--reason", "too fast"), ("allow", "AEM-G02", "--reason", "the fonts"),
                    ("use", "acme/P1"), ("stage", "end")]
        for c in commands:
            code, d = self.chat(a["nonce"], *c)
            self.assertEqual(code, 0, (c, d))
        for c in commands:
            code, d = self.chat("0" * 64, *c)
            self.assertEqual(code, 2, (c, d))
        records = [e for e in self.w.events() if e.get("via") == "chat"]
        self.assertTrue({"start", "approval", "rejection", "allow", "finish"} <= {e["event"] for e in records})
        self.assertTrue(all(e["prompt_id"] == a["prompt_id"] for e in records if e["event"] != "operator_prompt"))

    def test_inbox_commands_and_new_client_are_accepted_too(self):
        a = self.open()
        code, d = self.chat(a["nonce"], "inbox", "dismiss", "nothing", "--reason", "r")
        self.assertNotEqual((code, d.get("operator_only")), (2, True), d)  # past the operator check: it fails on the id
        code, d = self.chat(a["nonce"], "new-client", "beta", "--name", "Beta", "--design-system",
                            str(self.w.tmp / "Beta" / "DS"), "--projects-root", str(self.w.tmp / "Beta"),
                            env={"AEM_REGISTRY": str(self.w.tmp / "scratch-clients.json")})
        self.assertNotEqual((code, d.get("operator_only")), (2, True), d)

    def test_the_authority_ends_with_the_turn(self):
        a = self.open()
        self.render()
        self.assertEqual(self.chat(a["nonce"], "stage", "start", "G1")[0], 0)
        code, d = self.w.run("authority", "close", "--session", SESSION, check=True)
        self.assertEqual(d["closed"], [a["prompt_id"]])
        self.assertFalse((self.w.home / "nonces" / operator.nonce_hash(a["nonce"])).exists())
        code, d = self.chat(a["nonce"], "approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertIn("unknown, or its turn has ended", d["error"])
        self.assertEqual(self.w.approvals(), [])
        # and the guard is back to normal for the same nonce
        code, d = self.guard("Write", a["nonce"], file_path=str(self.w.project / "approvals.jsonl"), content="x")
        self.assertEqual((code, d["decision"], d["rule"]), (1, "deny", "AEM-G01"))

    def test_the_authority_ends_after_sixty_minutes_whatever_the_turn_does(self):
        a = self.open()
        path = self.w.home / "nonces" / operator.nonce_hash(a["nonce"])
        rec = json.loads(path.read_text())
        rec["expires_at"] = time.time() - 1  # what the clock does to a turn that ran for an hour
        path.write_text(json.dumps(rec))
        code, d = self.chat(a["nonce"], "stage", "start", "G1")
        self.assertEqual(code, 2)
        self.assertIn("expired", d["error"])
        code, d = self.guard("Write", a["nonce"], file_path=str(self.w.project / "approvals.jsonl"), content="x")
        self.assertEqual((code, d["decision"]), (1, "deny"))

    def test_closing_one_session_leaves_another_sessions_authority(self):
        a = self.open(session="s-one")
        b = self.open(session="s-two", turn="t9")
        self.w.run("authority", "close", "--session", "s-one", check=True)
        self.assertEqual(self.chat(a["nonce"], "stage", "start", "G1")[0], 2)
        self.assertEqual(self.chat(b["nonce"], "stage", "start", "G1")[0], 0)

    def test_each_use_is_listed_for_the_plugin_to_toast(self):
        a = self.open()
        self.render()
        self.chat(a["nonce"], "approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.chat(a["nonce"], "stage", "start", "G4", "x")
        self.chat(a["nonce"], "stage", "start", "G4", "x")  # fails (already open): not a use
        code, d = self.chat(a["nonce"], "authority", "uses")
        self.assertEqual((code, d["count"]), (0, 2), d)
        self.assertEqual([u["action"] for u in d["uses"]], ["approve x", "stage start G4 x"])
        self.assertTrue(all(u["excerpt"].startswith("Approve x at G4") for u in d["uses"]))
        code, d = self.chat(a["nonce"], "authority", "uses", "--after", "1")
        self.assertEqual([u["n"] for u in d["uses"]], [2])
        code, d = self.autonomous("authority", "uses")
        self.assertEqual((code, d["active"], d["uses"]), (0, False, []))


class ClientSaidOnChat(Chat):
    def decisions(self):
        return (self.w.ds / "acme-decisions.md").read_text()

    def test_refused_when_the_quote_is_not_in_the_prompt(self):
        a = self.open()
        before = self.decisions()
        code, d = self.chat(a["nonce"], "client-said", "--scope", "video", "--source", "Frame.io",
                            stdin="Make the whole thing louder.")
        self.assertEqual(code, 2, d)
        self.assertIn("paste Ada's exact words in your message", d["error"])
        self.assertEqual(self.decisions(), before)
        self.assertEqual([e for e in self.w.events() if e["event"] == "client_said"], [])

    def test_a_paraphrase_of_words_that_are_in_the_prompt_is_refused_too(self):
        a = self.open()
        code, d = self.chat(a["nonce"], "client-said", "--scope", "video", "--source", "Frame.io",
                            stdin="Could you keep the caption off the button? It reads fine without it.")  # newline became a space
        self.assertEqual(code, 2, d)

    def test_accepted_when_the_quote_is_verbatim_in_the_prompt(self):
        a = self.open()
        quote = "Could you keep the caption off the button?\nIt reads fine without it."
        code, d = self.chat(a["nonce"], "client-said", "--scope", "video", "--source", "Frame.io", stdin=quote + "\n")
        self.assertEqual(code, 0, d)
        text = self.decisions()
        self.assertIn("> Could you keep the caption off the button?\n> It reads fine without it.", text)
        self.assertIn(f"on their chat message ({a['prompt_id']})", text)
        ev = [e for e in self.w.events() if e["event"] == "client_said"][-1]
        self.assertEqual((ev["via"], ev["prompt_id"]), ("chat", a["prompt_id"]))

    def test_a_part_of_the_prompt_is_a_verbatim_quote(self):
        a = self.open()
        code, d = self.chat(a["nonce"], "client-said", "--scope", "channel", "--source", "WhatsApp",
                            stdin="It reads fine without it.")
        self.assertEqual(code, 0, d)

    def test_without_an_authority_the_one_time_nonce_path_is_unchanged(self):
        # the slash command: what the operator typed after the options is the quote; no prompt to compare with
        code, d = self.w.run("client-said", "--scope", "video", "--source", "Frame.io", stdin="Anything at all")
        self.assertEqual(code, 0, d)
        self.assertNotIn("chat message", self.decisions().split("Anything at all")[1].split("---")[0])


class GuardOnChat(Chat):
    def assertAllowedLogged(self, nonce, rule, tool, **args):
        n = len([e for e in self.w.events() if e["event"] == "allowed_by_operator_prompt"])
        code, d = self.guard(tool, nonce, **args)
        self.assertEqual((code, d["decision"]), (0, "allow"), d)
        self.assertEqual(d["allowed_by_operator_prompt"]["rule"], rule)
        logged = [e for e in self.w.events() if e["event"] == "allowed_by_operator_prompt"]
        self.assertEqual(len(logged), n + 1)
        self.assertEqual((logged[-1]["rule"], logged[-1]["prompt_id"], logged[-1]["tool"]), (rule, d["allowed_by_operator_prompt"]["prompt_id"], tool))
        return logged[-1]

    def test_the_guard_never_denies_and_logs_the_rule_it_would_have_hit(self):
        a = self.open()
        self.assertAllowedLogged(a["nonce"], "AEM-G01", "Write", file_path=str(self.w.project / "approvals.jsonl"), content="x")
        self.assertAllowedLogged(a["nonce"], "AEM-G01", "Edit", file_path=str(self.w.ds / "acme-decisions.md"),
                                 old_string="a", new_string="b")
        self.assertAllowedLogged(a["nonce"], "AEM-G01", "Bash", command="echo '{}' >> events.jsonl")
        self.assertAllowedLogged(a["nonce"], "AEM-G02", "Read", file_path="/Volumes/Other Client/secret.md")
        self.assertAllowedLogged(a["nonce"], "AEM-G02", "Bash", command="cat '/Volumes/Other Client/brief.md'")
        self.assertAllowedLogged(a["nonce"], "AEM-G03", "Bash", command="npx hyperframes snapshot --describe .")
        r = self.render("shot_v01.mp4")
        self.assertAllowedLogged(a["nonce"], "AEM-G05", "Bash", command=f"python3 place.py --fcpxml out/p.fcpxml '{r}'")
        self.assertAllowedLogged(a["nonce"], "AEM-G01", "Write", file_path=str(self.w.home / "nonces" / ("0" * 64)), content="x")
        self.assertEqual([e for e in self.w.events() if e["event"] == "denial"], [])
        ev = [e for e in self.w.events() if e["event"] == "allowed_by_operator_prompt"][0]
        self.assertEqual(ev["via"], "chat")
        self.assertTrue(ev["prompt_excerpt"].startswith("Approve x at G4"))

    def test_the_same_calls_in_an_autonomous_turn_are_denied_as_before(self):
        self.open()  # an authority exists on disk, but this turn does not carry it
        for tool, args, rule in (("Write", {"file_path": str(self.w.project / "events.jsonl"), "content": "{}"}, "AEM-G01"),
                                 ("Read", {"file_path": "/Volumes/Other Client/secret.md"}, "AEM-G02"),
                                 ("Bash", {"command": "npx hyperframes snapshot --describe ."}, "AEM-G03")):
            code, d = self.guard(tool, **args)
            self.assertEqual((code, d["decision"], d["rule"]), (1, "deny", rule), d)
        self.assertEqual([e for e in self.w.events() if e["event"] == "allowed_by_operator_prompt"], [])

    def test_a_calls_that_the_guard_would_allow_is_not_logged_as_overridden(self):
        a = self.open()
        code, d = self.guard("Read", a["nonce"], file_path=str(self.w.ds / "rules.md"))
        self.assertEqual((code, d), (0, {"ok": True, "decision": "allow"}))

    def test_a_standing_allow_is_not_used_up_on_a_turn_that_needs_none(self):
        self.w.run("allow", "snapshot --describe", "--reason", "once", "--once", check=True)
        a = self.open()
        self.guard("Bash", a["nonce"], command="npx hyperframes snapshot --describe .")
        self.assertEqual([e for e in self.w.events() if e["event"] == "allow_used"], [])


class Friction(Chat):
    """Found in the P2 session: G05 fired on reads of an FCPXML, and `~/…;` was read as a path with a semicolon.
    Both must work with and without an authority, because a turn may be autonomous."""

    def setUp(self):
        super().setUp()
        # A home outside the system folders the guard always allows (the test world itself is under
        # /var/folders, which is one), so a word read wrongly as a path really is outside. It need not exist.
        self.home_dir = Path("/Users/aem-test-nobody")
        reg = json.loads(self.w.registry.read_text())
        reg["shared_paths"] = ["~/Tools/fcp-edit-workflow"]
        self.w.registry.write_text(json.dumps(reg))
        self.fcpxml = self.w.project / "Videos and Media" / "RoughCut.fcpxml"
        self.fcpxml.parent.mkdir(parents=True)
        self.fcpxml.write_text("<fcpxml/>")
        (self.w.project / "renders" / "place_v01.mp4").write_bytes(b"x")  # a render nobody approved

    def both(self, tool, **args):
        """The call, without an authority and with one: allowed both times, and nothing logged as overridden."""
        a = self.open()
        for nonce in (None, a["nonce"]):
            env = {"HOME": str(self.home_dir), **({"AEM_OPERATOR_TURN": nonce} if nonce else {})}
            code, d = self.w.run("guard", stdin=json.dumps({"tool": tool, "input": args, "cwd": str(self.w.project)}),
                                 operator=False, env=env)
            self.assertEqual((code, d["decision"]), (0, "allow"), (nonce is not None, args, d))
            self.assertNotIn("allowed_by_operator_prompt", d, args)
        self.assertEqual([e for e in self.w.events() if e["event"] in ("denial", "allowed_by_operator_prompt")], [])

    def test_g05_never_fires_on_reading_an_fcpxml(self):
        f = "Videos and Media/RoughCut.fcpxml"
        for command in (f"cat '{f}'",
                        f"grep -n 'asset' '{f}' | head",
                        f"unzip -p 'Videos and Media/RoughCut.fcpxmld.zip' Info.fcpxml | head -50",
                        f"unzip -l RoughCut.fcpxmld.zip && cat '{f}' | wc -l",
                        f"xmllint --xpath '//asset' '{f}'",
                        f"python3 -c \"import xml.etree.ElementTree as ET; print(ET.parse('{f}').getroot())\"",
                        f"python3 - <<'EOF'\nimport xml.etree.ElementTree as ET\nr = ET.parse('{f}').getroot()\nprint(len(r))\nEOF",
                        f"ffprobe -v error renders/place_v01.mp4",
                        f"aem check-approval renders/place_v01.mp4",
                        f"head -c 200 '{f}' 2>/dev/null"):
            self.both("Bash", command=command)

    def test_a_placement_that_writes_is_still_gated_on_a_render_nobody_approved(self):
        r = self.w.project / "renders" / "place_v01.mp4"
        for command in ("python3 place.py --fcpxml out/p.fcpxml renders/place_v01.mp4",
                        f"python3 place.py --fcpxml out/p.fcpxml '{r}'",
                        f"cp '{r}' '/tmp/Animations Done/x.mp4'  # deliver",
                        f"python3 - <<'EOF'\nopen('out/p.fcpxml','w').write('<asset src=\"file://{r}\"/>')\nEOF"):
            code, d = self.guard("Bash", command=command)
            self.assertEqual((code, d.get("rule")), (1, "AEM-G05"), (command, d))

    def test_the_fcp_edit_workflow_folder_with_a_semicolon_a_pipe_or_a_bracket_after_it(self):
        t = "~/Tools/fcp-edit-workflow"
        for command in (f"cd {t}; ls",
                        f"ls {t};",
                        f"ls {t}; echo done",
                        f"ls {t}|head",
                        f"(cd {t} && ls)",
                        f"cd {t}&&ls",
                        f"ls {t} >/dev/null 2>&1; echo $?",
                        f"x=$(ls {t}); echo $x",
                        f"cd \"{t}\"; ls",
                        f"ls `ls -d {t}`",
                        f"{t}/fcp-edit --help; python3 {t}/fcp-edit '{self.fcpxml}'",
                        f"python3 {t}/fcp-edit read 'Videos and Media/RoughCut.fcpxml'"):
            self.both("Bash", command=command)

    def test_a_path_that_really_is_outside_is_still_outside(self):
        code, d = self.w.run("guard", operator=False, env={"HOME": str(self.home_dir)},
                             stdin=json.dumps({"tool": "Bash", "cwd": str(self.w.project), "input": {"command": "cd ~/Elsewhere; ls"}}))
        self.assertEqual((code, d.get("rule")), (1, "AEM-G02"), d)

    def test_tokens_split_like_a_shell(self):
        from aem import guard
        words = guard.bash_paths("cd ~/Tools/x; ls ./a|head ../b&&cat '/c d'>/e", str(self.w.project))
        self.assertEqual([p.name for p in words], ["x", "a", "b", "c d", "e"])


class Integrity(Chat):
    """Phase 4: anything written to a ledger outside AEM is detected; the operator accepts it with accept-edit."""

    def hand_write(self, name="events.jsonl", line='{"ts": "2026-10-06T12:00:00+05:30", "event": "approval", "scene": "x"}'):
        with open(self.w.project / name, "a") as f:
            f.write(line + "\n")

    def integrity(self):
        return self.w.run("integrity", operator=False)

    def test_clean_after_aem_wrote_everything(self):
        self.w.run("stage", "start", "G1", check=True)
        self.render()
        self.w.run("approve", "x", "renders/x_v01.mp4", "--gate", "G4", check=True)
        code, d = self.integrity()
        self.assertEqual((code, d["ok"], d["findings"]), (0, True, 0), d)

    def test_writing_events_directly_in_an_autonomous_turn_is_refused(self):
        code, d = self.guard("Write", file_path=str(self.w.project / "events.jsonl"), content="{}")
        self.assertEqual((code, d["decision"], d["rule"]), (1, "deny", "AEM-G01"), d)
        code, d = self.guard("Bash", command="echo '{}' >> events.jsonl")
        self.assertEqual((code, d["rule"]), (1, "AEM-G01"))
        for target in (self.w.project / ".aem-integrity" / "events.jsonl.jsonl",):
            code, d = self.guard("Write", file_path=str(target), content="x")
            self.assertEqual((code, d["rule"]), (1, "AEM-G01"), target)

    def test_the_same_write_in_an_operator_turn_is_allowed_logged_and_flagged_until_accept_edit(self):
        self.w.run("stage", "start", "G1", check=True)
        a = self.open(prompt="Add a line to events.jsonl noting that Ada called on the phone.")
        # 1. the guard lets the agent's write through and logs it, naming the prompt
        code, d = self.guard("Write", a["nonce"], file_path=str(self.w.project / "events.jsonl"), content="x")
        self.assertEqual((code, d["decision"], d["allowed_by_operator_prompt"]["rule"]), (0, "allow", "AEM-G01"), d)
        # 2. the write itself (what the Write tool does)
        self.hand_write(line='{"ts": "2026-10-06T12:00:00+05:30", "gate": "G1", "event": "note", "note": "Ada called"}')
        # 3. the integrity check flags the hand-written line, and says the operator's prompt let it through
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (1, False), r)
        self.assertEqual((r["findings"], r["unexplained"], r["during_operator_prompt"]), (1, 0, 1), r)
        f = next(x for x in r["files"] if x["name"] == "events.jsonl")
        self.assertEqual(f["findings"][0]["kind"], "inserted")
        self.assertIn("Ada called", f["findings"][0]["now"][0]["text"])
        self.assertEqual(f["allowed_by_operator_prompt"][0]["prompt_id"], a["prompt_id"])
        self.assertIn(a["prompt_id"], f["explanation"])
        self.assertIn("1 ledger edit(s) to review", self.w.run("status", operator=False)[1]["statusline"])
        # 4. it stays flagged: the agent cannot accept it in an autonomous turn
        code, d = self.autonomous("accept-edit")
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertEqual(self.integrity()[0], 1)
        # 5. accepted on the operator's message: recorded with the prompt, then clean
        b = self.open(prompt="Yes, accept that edit.", turn="t2")
        code, d = self.chat(b["nonce"], "accept-edit", "--reason", "I asked for that line")
        self.assertEqual(code, 0, d)
        self.assertEqual(d["accepted"][0]["file"], "events.jsonl")
        acc = [e for e in self.w.events() if e["event"] == "edit_accepted"]
        self.assertEqual((len(acc), acc[0]["file"], acc[0]["via"], acc[0]["prompt_id"]), (1, "events.jsonl", "chat", b["prompt_id"]))
        self.assertEqual(acc[0]["explained_by"][0]["prompt_id"], a["prompt_id"])
        self.assertEqual(acc[0]["note"], "I asked for that line")
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True), r)
        # 6. a later hand edit is flagged again
        self.hand_write(line='{"event": "another"}')
        self.assertEqual(self.integrity()[0], 1)

    def test_a_line_nothing_logged_is_reported_as_outside_any_operator_prompt(self):
        self.w.run("stage", "start", "G1", check=True)
        self.hand_write()
        code, r = self.integrity()
        self.assertEqual((code, r["unexplained"], r["during_operator_prompt"]), (1, 1, 0), r)
        f = next(x for x in r["files"] if x["name"] == "events.jsonl")
        self.assertIn("outside any recorded operator prompt", f["explanation"])
        # the plugin's context tells the agent, and no agent can accept it
        _, ctx = self.w.run("context", operator=False)
        self.assertIn("AEM integrity: 1 ledger difference(s) in events.jsonl", ctx["text"])

    def test_edits_and_removals_of_aem_lines_are_found(self):
        self.w.run("stage", "start", "G1", check=True)
        self.render()
        self.w.run("approve", "x", "renders/x_v01.mp4", "--gate", "G4", check=True)
        path = self.w.project / "approvals.jsonl"
        text = path.read_text()
        path.write_text(text.replace('"gate": "G4"', '"gate": "G5"'))  # the approval now says another gate
        code, r = self.integrity()
        self.assertEqual(code, 1, r)
        self.assertEqual(next(x for x in r["files"] if x["name"] == "approvals.jsonl")["findings"][0]["kind"], "edited")
        path.write_text("")  # and now it is gone
        code, r = self.integrity()
        f = next(x for x in r["files"] if x["name"] == "approvals.jsonl")
        self.assertEqual((code, f["findings"][0]["kind"], f["findings"][0]["removed_count"]), (1, "removed", 1), r)

    def test_the_decisions_file_is_a_ledger_too_and_client_said_does_not_accept_a_hand_edit(self):
        self.w.run("client-said", "--scope", "video", "--source", "email", stdin="First words", check=True)
        path = self.w.ds / "acme-decisions.md"
        self.assertEqual(self.integrity()[0], 0)
        path.write_text(path.read_text().replace("> First words", "> First words, edited by hand"))
        code, r = self.integrity()
        self.assertEqual(code, 1, r)
        self.w.run("client-said", "--scope", "video", "--source", "email", stdin="Second words", check=True)
        code, r = self.integrity()
        f = next(x for x in r["files"] if x["name"] == "acme-decisions.md")
        self.assertEqual(code, 1, r)
        self.assertEqual(len(f["findings"]), 1, f)  # only the hand edit; the second entry is AEM's
        self.assertIn("edited by hand", f["findings"][0]["now"][0]["text"])

    def test_no_baseline_is_reported_not_guessed_and_the_first_write_makes_one(self):
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True))
        self.assertIn("events.jsonl", r["no_baseline"])
        self.hand_write(name="events.jsonl")  # an older, pre-0.9 line
        self.w.run("stage", "start", "G1", check=True)  # AEM's first write: the old line is the baseline
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True), r)
        manifest = [json.loads(l) for l in (self.w.project / ".aem-integrity" / "events.jsonl.jsonl").read_text().splitlines()]
        self.assertEqual(manifest[0]["t"], "baseline")
        self.assertEqual(len(manifest[0]["hashes"]), 1)

    def test_accept_edit_with_nothing_to_accept_says_so_and_names_unknown_files(self):
        self.w.run("stage", "start", "G1", check=True)
        code, d = self.w.run("accept-edit")
        self.assertEqual((code, d["accepted"]), (0, []))
        code, d = self.w.run("accept-edit", "--file", "rules.md")
        self.assertEqual(code, 2, d)


class TestRunLeavesNoTrace(Chat):
    def test_a_whole_authority_flow_leaves_the_real_aem_home_and_registry_untouched(self):
        before = isolation.snapshot()
        a = self.open()
        self.render()
        self.chat(a["nonce"], "approve", "x", "renders/x_v01.mp4", "--gate", "G4")
        self.guard("Write", a["nonce"], file_path=str(self.w.project / "events.jsonl"), content="x")
        self.w.run("authority", "close", "--session", SESSION, check=True)
        self.assertEqual(isolation.changed(before, isolation.snapshot()), [])
        self.assertTrue(str(self.w.home).startswith(str(self.w.tmp)))
        self.assertNotEqual(Path(os.environ["AEM_HOME"]).resolve(), isolation.REAL_AEM_HOME.resolve())


if __name__ == "__main__":
    unittest.main()
