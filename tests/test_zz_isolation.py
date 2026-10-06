"""The test run never touched the operator's real AEM state.

Named test_zz so `unittest discover` runs it last: helpers.py snapshots ~/.aem and
registry/clients.json when the test modules are imported, before any test runs, and this compares.
(tests/run.sh does the same around the plugin tests and the whole run.)
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import isolation
from helpers import AEM, REAL_STATE_BEFORE, SANDBOX


class Isolation(unittest.TestCase):
    def test_process_points_at_the_sandbox(self):
        self.assertEqual(os.environ["AEM_HOME"], str(SANDBOX.home))
        self.assertEqual(os.environ["AEM_REGISTRY"], str(SANDBOX.registry))
        self.assertNotEqual(Path(os.environ["AEM_HOME"]).resolve(), isolation.REAL_AEM_HOME.resolve())
        self.assertEqual(isolation.problems(SANDBOX.root), [])

    def test_sandbox_registry_reaches_no_real_client_folder(self):
        reg = json.loads(SANDBOX.registry.read_text())
        for c in reg["clients"]:
            for key in ("design_system", "projects_root"):
                self.assertTrue(Path(c[key]).is_relative_to(SANDBOX.root), f"{c['id']} {key}: {c[key]}")

    def test_a_world_less_aem_call_lands_in_the_sandbox(self):
        p = subprocess.run([sys.executable, str(AEM), "status", "--json"], capture_output=True, text=True)
        self.assertEqual(json.loads(p.stdout)["active"], False)

    def test_verify_refuses_unsafe_folders(self):
        self.assertTrue(isolation.problems(isolation.REAL_AEM_HOME.parent))  # no sandbox marker
        sb = isolation.sandbox("aem-iso-test-")
        try:
            reg = json.loads(sb.registry.read_text())
            reg["clients"][0]["projects_root"] = "/Volumes/T7 Red"
            sb.registry.write_text(json.dumps(reg))
            self.assertTrue(any("outside the sandbox" in p for p in isolation.problems(sb.root)))
        finally:
            sb.cleanup()

    def test_zz_real_aem_state_unchanged_by_the_run(self):
        self.assertEqual(isolation.changed(REAL_STATE_BEFORE, isolation.snapshot()), [])


if __name__ == "__main__":
    unittest.main()
