"""Phase 1 (0.8.0): the project comes from where you work, never from stored global state.

Each test is named after the 6 October 2026 incident it guards against: a test run overwrote the one
global active-project file with a registry and folders under /tmp, and every session trusted it.
"""
import json
import os
import shutil
import unittest
from pathlib import Path

import isolation
from helpers import REPO, REAL_STATE_BEFORE, WorldCase


def second_project(w, name="P2", folder="P2 - Second", fps="25/1"):
    """A second registered project in the world's client."""
    (w.root / folder).mkdir(parents=True, exist_ok=True)
    (w.root / folder / "frame.md").write_text(f'---\nfps           : "{fps}"\n---\n', encoding="utf-8")
    reg = json.loads(w.registry.read_text())
    reg["clients"][0]["projects"][name] = {"dir": folder}
    w.registry.write_text(json.dumps(reg, indent=2))
    return w.root / folder


class ResolveFromWhereYouWork(WorldCase):
    def status(self, cwd, env=None):
        return self.w.run("status", cwd=cwd, env=env)

    def test_a_session_in_the_project_folder_resolves_it_with_no_use(self):
        code, d = self.status(self.w.project)
        self.assertEqual(code, 0)
        self.assertEqual((d["active"], d["client"], d["project"]), (True, "acme", "P1"))
        self.assertEqual(d["resolution"]["source"], "folder")
        self.assertFalse((self.w.home / "active.json").exists())  # nothing was stored to get here

    def test_a_subfolder_resolves_to_its_project(self):
        sub = self.w.project / "compositions"
        _, d = self.status(sub)
        self.assertEqual(d["project"], "P1")

    def test_the_longest_matching_project_folder_wins(self):
        inner = self.w.project / "nested"
        (inner).mkdir()
        (inner / "frame.md").write_text('---\nfps           : "25/1"\n---\n')
        reg = json.loads(self.w.registry.read_text())
        reg["clients"][0]["projects"]["P1-inner"] = {"dir": "P1 - Test/nested"}
        self.w.registry.write_text(json.dumps(reg))
        _, d = self.status(inner)
        self.assertEqual(d["project"], "P1-inner")
        _, d = self.status(self.w.project)
        self.assertEqual(d["project"], "P1")

    def test_a_session_in_the_aem_repo_resolves_no_project(self):
        code, d = self.status(REPO)
        self.assertEqual(code, 0)
        self.assertFalse(d["active"])
        self.assertEqual(d["resolution"]["source"], "none")

    def test_a_folder_in_the_design_system_resolves_the_client_only(self):
        code, d = self.status(self.w.ds)
        self.assertEqual(code, 0)
        self.assertEqual((d["active"], d["client"], d["project"]), (False, "acme", None))
        self.assertEqual(d["resolution"]["source"], "folder (design system)")
        # A command that needs a project says so instead of guessing one.
        code, d = self.w.run("stage", "start", "G1", cwd=self.w.ds)
        self.assertEqual(code, 2)
        self.assertIn("not in a project", d["error"])

    def test_the_projects_root_itself_is_not_a_project(self):
        _, d = self.status(self.w.root)
        self.assertFalse(d["active"])

    def test_p2_style_second_project_resolves_by_folder(self):
        second_project(self.w)
        _, d = self.status(self.w.root / "P2 - Second")
        self.assertEqual((d["project"], d["fps"]["num"], d["fps"]["den"]), ("P2", 25, 1))


class SessionPinAndEnv(WorldCase):
    def setUp(self):
        super().setUp()
        self.p2 = second_project(self.w)

    def test_env_beats_the_folder(self):
        _, d = self.w.run("status", cwd=self.w.project, env={"AEM_PROJECT": "acme/P2"})
        self.assertEqual((d["project"], d["resolution"]["source"]), ("P2", "env"))
        self.assertIn("AEM_PROJECT=acme/P2", d["resolution"]["detail"])

    def test_session_pin_beats_the_folder_and_is_named_as_a_pin(self):
        # The plugin passes its pin as AEM_PROJECT plus AEM_PROJECT_SOURCE=session-pin.
        _, d = self.w.run("status", cwd=self.w.project,
                          env={"AEM_PROJECT": "acme/P2", "AEM_PROJECT_SOURCE": "session-pin"})
        self.assertEqual((d["project"], d["resolution"]["source"]), ("P2", "session pin"))

    def test_env_works_with_no_folder_at_all(self):
        _, d = self.w.run("status", cwd=REPO, env={"AEM_PROJECT": "acme/P1"})
        self.assertEqual((d["project"], d["resolution"]["source"]), ("P1", "env"))

    def test_a_bad_env_value_fails_loudly_instead_of_falling_back_to_the_folder(self):
        code, d = self.w.run("status", cwd=self.w.project, env={"AEM_PROJECT": "acme"})
        self.assertEqual(code, 2)
        self.assertIn("AEM_PROJECT", d["error"])
        code, d = self.w.run("status", cwd=self.w.project, env={"AEM_PROJECT": "nobody/P1"})
        self.assertEqual(code, 2)
        self.assertIn("unknown client", d["error"])

    def test_every_command_follows_the_pin_not_the_folder(self):
        # The ledger is written in the pinned project's folder.
        self.w.run("stage", "start", "G1", cwd=self.w.project, env={"AEM_PROJECT": "acme/P2"}, check=True)
        self.assertTrue((self.p2 / "events.jsonl").exists())
        self.assertFalse((self.w.project / "events.jsonl").exists())


class StatusSaysHowItResolved(WorldCase):
    def test_status_shows_project_folder_design_system_fps_and_how(self):
        r = self.w.run_raw("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        for needle in ("project  acme/P1", "resolved from folder", str(self.w.project), str(self.w.ds), "24000/1001",
                       "from frame.md"):
            self.assertIn(needle, r.stdout)
        _, d = self.w.run("status")
        res = d["resolution"]
        self.assertEqual((res["project"], res["source"], res["registry"], res["fps"]),
                         ("acme/P1", "folder", "AEM_REGISTRY", "frame.md"))

    def test_status_with_nothing_resolved_says_so_and_how_to_fix_it(self):
        r = self.w.run_raw("status", cwd=self.w.tmp)
        self.assertIn("No project resolved here (folder not registered)", r.stdout)
        self.assertIn("AEM_PROJECT", r.stdout)


class RegistryIsNeverStoredState(WorldCase):
    def test_the_registry_comes_from_the_environment_not_from_a_file(self):
        # Regression: active.json carried a "registry" path (a /tmp copy) that every session then trusted.
        self.w.use()
        hint = json.loads((self.w.home / "active.json").read_text())
        hint["registry"] = "/private/tmp/evil/clients.json"
        (self.w.home / "active.json").write_text(json.dumps(hint))
        _, d = self.w.run("status")
        self.assertEqual(d["registry"], str(self.w.registry.resolve()))

    def test_nothing_but_status_reads_the_last_used_hint(self):
        # Regression: the stale hint made every session record into a /tmp project.
        self.w.use()
        (self.w.home / "active.json").write_text(json.dumps(
            {"client": "acme", "project": "P1", "project_dir": "/private/tmp/x/P1 - Test"}))
        for cmd in (("context",), ("observe",), ("rendered",), ("stage", "auto", "prompt")):
            code, d = self.w.run(*cmd, cwd=self.w.tmp, stdin="{}")
            self.assertNotEqual(d.get("project"), "P1", cmd)
        _, g = self.w.run("observe", cwd=self.w.tmp,
                          stdin=json.dumps({"tool": "Read", "input": {"file_path": "/Volumes/Other/x"}, "cwd": str(self.w.tmp)}))
        self.assertFalse(g["observed"])  # no project resolved: nothing recorded, whatever the hint says


class RefuseTemporaryProjects(WorldCase):
    """Regression (6 Oct 2026): a project under /private/tmp became the active one."""

    def setUp(self):
        super().setUp()
        self.nosb = {"AEM_SANDBOX": "0"}

    def test_a_tmp_project_is_refused_without_the_sandbox_flag(self):
        reg = json.loads(self.w.registry.read_text())
        c = reg["clients"][0]
        tmp_root = Path("/private/tmp") / f"aem-refuse-{os.getpid()}"
        (tmp_root / "P9 - Copy").mkdir(parents=True)
        (tmp_root / "P9 - Copy" / "frame.md").write_text('---\nfps           : "25/1"\n---\n')
        try:
            c["projects_root"] = str(tmp_root)
            c["projects"]["P9"] = {"dir": "P9 - Copy"}
            self.w.registry.write_text(json.dumps(reg))
            code, d = self.w.run("status", cwd=tmp_root / "P9 - Copy", env=self.nosb)
            self.assertEqual(code, 2)
            self.assertIn("is under /tmp", d["error"])
            self.assertIn("AEM_SANDBOX=1", d["error"])
            code, d = self.w.run("status", cwd=self.w.tmp, env={**self.nosb, "AEM_PROJECT": "acme/P9"})
            self.assertEqual(code, 2)
            self.assertIn("refusing project acme/P9", d["error"])
            code, d = self.w.run("use", "acme/P9", env=self.nosb)
            self.assertEqual(code, 2)
            self.assertFalse((self.w.home / "active.json").exists())
            # The flag allows it (tests and acceptance runs).
            code, d = self.w.run("status", cwd=tmp_root / "P9 - Copy", env={"AEM_SANDBOX": "1"})
            self.assertEqual((code, d["project"]), (0, "P9"))
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    def test_a_project_outside_the_registry_roots_is_refused(self):
        outside = self.w.tmp / "Elsewhere" / "P7 - Loose"
        outside.mkdir(parents=True)
        (outside / "frame.md").write_text('---\nfps           : "25/1"\n---\n')
        reg = json.loads(self.w.registry.read_text())
        reg["clients"][0]["projects"]["P7"] = {"dir": "../Elsewhere/P7 - Loose"}
        self.w.registry.write_text(json.dumps(reg))
        code, d = self.w.run("status", cwd=outside, env=self.nosb)
        self.assertEqual(code, 2)
        self.assertIn("outside the projects root and design system", d["error"])


class StaleHintMigration(WorldCase):
    """The leftover from the acceptance run: active.json pointing at a /tmp copy."""

    def test_a_hint_outside_the_registry_roots_is_renamed_and_said_so(self):
        (self.w.home / "active.json").write_text(json.dumps({
            "client": "acme", "project": "P1", "project_dir": "/private/tmp/scratch/accept/Acme/P1 - Test",
            "registry": "/private/tmp/scratch/accept/clients.json", "set_at": "2026-10-06T18:21:27+05:30"}))
        env = {"AEM_SANDBOX": "0"}
        code, d = self.w.run("status", cwd=self.w.tmp, env=env)
        self.assertEqual(code, 0)
        self.assertIn("active.json.stale", d["hint_note"])
        self.assertIn("/private/tmp/scratch/accept/Acme/P1 - Test", d["hint_note"])
        self.assertFalse((self.w.home / "active.json").exists())
        self.assertTrue((self.w.home / "active.json.stale").exists())
        self.assertIsNone(d["last_used_hint"])
        # And it is said in the plain-text status too, once.
        (self.w.home / "active.json").write_text((self.w.home / "active.json.stale").read_text())
        r = self.w.run_raw("status", cwd=self.w.tmp, env=env)
        self.assertIn("moved", r.stdout)

    def test_a_good_hint_is_shown_as_a_hint_only_in_a_bare_terminal(self):
        self.w.use()
        r = self.w.run_raw("status", cwd=self.w.tmp)
        self.assertIn("last used (a hint only, nothing reads it): acme/P1", r.stdout)
        _, d = self.w.run("status", cwd=self.w.tmp)
        self.assertEqual(d["last_used_hint"]["project"], "P1")
        self.assertFalse(d["active"])  # showing the hint resolves nothing


class TestsLeaveTheRealResolutionAlone(unittest.TestCase):
    def test_the_real_aem_state_is_what_it_was_before_the_run_started(self):
        self.assertEqual(isolation.changed(REAL_STATE_BEFORE, isolation.snapshot()), [])


if __name__ == "__main__":
    unittest.main()
