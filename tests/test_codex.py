"""aem codex-hook: Codex hook events (shapes from the Codex hooks reference) answered with AEM's record.

The hook keeps context, ledger events and the render sentinel. It never denies a call: PreToolUse only records it."""
import json
import time
import unittest

from helpers import HAVE_FFMPEG, WorldCase, make_video

BASE = {"session_id": "codex-s1", "transcript_path": "/tmp/t.jsonl", "model": "gpt-x", "permission_mode": "default"}


class CodexHook(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        self.w.use()

    def hook(self, event, **fields):
        req = {**BASE, "hook_event_name": event, "cwd": str(self.w.project), **fields}
        code, out = self.w.run("codex-hook", stdin=json.dumps(req), cwd=fields.get("cwd"))
        self.assertEqual(code, 0)
        return out

    def pre(self, tool, tool_input, tid="call-1"):
        return self.hook("PreToolUse", turn_id="t1", tool_name=tool, tool_use_id=tid, tool_input=tool_input)

    def observed(self):
        return [e for e in self.w.events() if e["event"] == "observed"]

    def test_session_start_gives_context_and_records(self):
        out = self.hook("SessionStart", source="startup")
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("# Aavkar Educational Motion Studio (AEM)", text)
        self.assertIn("In Codex: AEM has no slash commands here", text)
        ev = self.w.events()[-1]
        self.assertEqual((ev["event"], ev["agent"], ev["session"]), ("session_start", "codex", "codex-s1"))

    def test_pre_tool_use_never_denies_and_records_the_call(self):
        for command in ("echo x >> events.jsonl", "npx hyperframes snapshot --describe .", "ls renders",
                        "cat ~/Tools/fcp-edit-workflow/README.md; ls ~/Tools/fcp-edit-workflow;"):
            self.assertEqual(self.pre("Bash", {"command": command}), {}, command)
        obs = self.observed()
        self.assertEqual([e["command"] for e in obs][:2], ["echo x >> events.jsonl", "npx hyperframes snapshot --describe ."])
        self.assertEqual((obs[0]["agent"], obs[0]["session"], obs[0]["writes"]), ("codex", "codex-s1", ["events.jsonl"]))

    def test_apply_patch_is_recorded_file_by_file(self):
        patch = ("*** Begin Patch\n*** Update File: notes.md\n@@\n-a\n+b\n"
                 f"*** Add File: {self.w.ds}/acme-decisions.md\n+a line by hand\n*** End Patch\n")
        self.assertEqual(self.pre("apply_patch", {"command": patch}), {})
        ev = self.observed()[-1]
        self.assertEqual(ev["tool"], "apply_patch")
        self.assertEqual(ev["writes"][0], "notes.md")
        self.assertTrue(ev["writes"][1].endswith("acme-decisions.md"))

    def test_an_unapproved_delivery_is_recorded_not_asked_about(self):
        r = self.w.project / "renders" / "shot_v01.mp4"
        r.write_bytes(b"render")
        patch = f'*** Begin Patch\n*** Add File: out/p.fcpxml\n+<asset src="file://{r}"/>\n*** End Patch\n'
        self.assertEqual(self.pre("apply_patch", {"command": patch}), {})
        self.assertEqual(self.observed()[-1]["delivery"]["media"][0]["state"], "none")
        self.w.run("approve", "shot", str(r), "--gate", "G4", check=True)
        self.assertEqual(self.pre("apply_patch", {"command": patch}), {})
        self.assertEqual(self.observed()[-1]["delivery"]["media"][0]["state"], "approved")

    def test_mcp_tools_are_not_recorded(self):
        self.assertEqual(self.pre("mcp__filesystem__write_file", {"path": str(self.w.project / "events.jsonl")}), {})
        self.assertEqual(self.observed(), [])

    def test_prompt_turn_and_session_end_are_recorded(self):
        self.hook("UserPromptSubmit", turn_id="t9", prompt="render the scene")
        self.hook("Stop", turn_id="t9", stop_hook_active=False, last_assistant_message="done")
        self.hook("SessionEnd", reason="other")
        evs = [(e["event"], e.get("turn")) for e in self.w.events()]
        self.assertEqual(evs, [("prompt", None), ("turn_start", "t9"), ("turn_end", "t9"), ("session_end", None)])

    def test_session_end_ends_a_stage_aem_inferred(self):
        self.pre("Bash", {"command": "cp a.md shotlist.md"})
        self.assertEqual([e["event"] for e in self.w.events()], ["stage_inferred", "observed"])
        self.hook("SessionEnd", reason="other")
        fin = self.w.events()[-1]
        self.assertEqual((fin["event"], fin["gate"], fin["inferred"]), ("finish", "G2", True))

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
    def test_render_sentinel_after_bash(self):
        cmd = "hyperframes render . -o renders/a_v01.mp4"
        self.assertEqual(self.pre("Bash", {"command": cmd}, tid="r1"), {})
        time.sleep(0.05)
        make_video(self.w.project / "renders" / "a_v01.mp4", frames=20)
        out = self.hook("PostToolUse", turn_id="t1", tool_name="Bash", tool_use_id="r1",
                        tool_input={"command": cmd}, tool_response="ok")
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("AEM checked 1 render(s)", text)
        self.assertIn("renders/a_v01.mp4", text)
        self.assertEqual([e["event"] for e in self.w.events()][-1], "render_check")
        self.assertIn("stage_inferred", [e["event"] for e in self.w.events()])  # no stage was open: G4 inferred
        # The pending start time is consumed.
        self.assertFalse((self.w.home / "codex" / "pending" / "r1.json").exists())

    def test_no_project_where_codex_runs(self):
        here = {"cwd": str(self.w.tmp)}
        out = self.hook("SessionStart", source="startup", **here)
        self.assertIn("no project is resolved", out["hookSpecificOutput"]["additionalContext"])
        self.assertIn("start Codex in the project's folder", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.hook("PreToolUse", turn_id="t1", tool_name="Bash", tool_use_id="c",
                                   tool_input={"command": "ls"}, **here), {})
        self.assertEqual(self.w.events(), [])  # nothing is recorded without a project

    def test_bad_input_fails_open(self):
        code, out = self.w.run("codex-hook", stdin="not json")
        self.assertEqual((code, out), (0, {}))


class CodexConfig(WorldCase):
    def test_toml_and_json_name_every_event_with_one_command(self):
        code, d = self.w.run("codex-config")
        self.assertEqual(code, 0)
        lines = [l for l in d["config"].splitlines() if " = [" in l]
        self.assertEqual([l.split(" = ")[0] for l in lines],
                         ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"])
        self.assertTrue(d["command"].endswith(" codex-hook"))
        self.assertTrue(all(json.dumps(d["command"]) in l for l in lines))
        code, j = self.w.run("codex-config", "--format", "json")
        cfg = json.loads(j["config"])
        self.assertEqual(cfg["hooks"]["PreToolUse"][0]["matcher"], "^(Bash|apply_patch|Edit|Write)$")
        self.assertEqual(cfg["hooks"]["PostToolUse"][0]["hooks"][0]["timeout"], 600)
