"""Offline tests for the skill scripts. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "fivem-development" / "scripts"
FIX = Path(__file__).resolve().parent / "fixtures"
BAD = FIX / "bad_resource"


def run(script: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.res = run("audit.py", str(BAD), "--json")
        self.rules = {f["rule"] for f in json.loads(self.res.stdout)}

    def test_exit_code_on_critical(self):
        self.assertEqual(self.res.returncode, 1)

    def test_detects_backdoor(self):
        self.assertTrue({"rce-assert-load", "known-backdoor", "rce-load-http"} <= self.rules)

    def test_detects_sql_injection(self):
        self.assertIn("sql-concat", self.rules)

    def test_detects_trust_and_perf_issues(self):
        for rule in ("client-money-event", "loop-without-wait", "net-event-no-source", "esx-getsharedobject-event",
                     "manifest-old-fxversion", "manifest-mysql-async", "manifest-no-game"):
            self.assertIn(rule, self.rules)


class ManifestTests(unittest.TestCase):
    def test_bad_manifest(self):
        res = run("manifest.py", str(BAD))
        self.assertEqual(res.returncode, 1)
        self.assertIn("game missing", res.stdout)
        self.assertIn("deprecated DB wrapper", res.stdout)


class NativesTests(unittest.TestCase):
    env = {"FIVEM_SKILL_CACHE": str(FIX / "natives_cache")}

    def test_wrong_side_detection(self):
        res = run("natives.py", "check", str(BAD), env=self.env)
        self.assertEqual(res.returncode, 1)
        self.assertIn("GetPlayerIdentifierByType() is server-only", res.stdout)
        self.assertIn("PlayerPedId() is client-only", res.stdout)

    def test_dual_side_native_not_flagged(self):
        res = run("natives.py", "check", str(BAD), env=self.env)
        self.assertNotIn("GetPlayerPed()", res.stdout)

    def test_show_digit_underscore_name(self):
        res = run("natives.py", "show", "GetGroundZFor_3dCoord", env=self.env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("GET_GROUND_Z_FOR_3D_COORD", res.stdout)

    def test_lua_name_conversion(self):
        sys.path.insert(0, str(SCRIPTS))
        try:
            import natives  # noqa: E402
        finally:
            sys.path.pop(0)
        self.assertEqual(natives.lua_name("GET_GROUND_Z_FOR_3D_COORD", "0x1"), "GetGroundZFor_3dCoord")
        self.assertEqual(natives.lua_name("_GET_ENTITY_X", "0x1"), "GetEntityX")
        self.assertEqual(natives.lua_name("_0xABCDEF", "0xABCDEF"), "N_0xabcdef")


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scaffold_is_clean(self):
        self.assertEqual(run("scaffold.py", "demo_res", "--out", str(self.tmp)).returncode, 0)
        dest = self.tmp / "demo_res"
        self.assertEqual(run("manifest.py", str(dest)).returncode, 0)
        audit = run("audit.py", str(dest), "--min", "high")
        self.assertEqual(audit.returncode, 0, audit.stdout)
        leftovers = [p for p in dest.rglob("*") if p.is_file() and "{{" in p.read_text(encoding="utf-8")]
        self.assertEqual(leftovers, [])
        self.assertNotIn("@nui", (dest / "fxmanifest.lua").read_text(encoding="utf-8"))
        self.assertFalse((dest / "client" / "nui.lua").exists())

    def test_scaffold_nui(self):
        self.assertEqual(run("scaffold.py", "demo_ui", "--nui", "--out", str(self.tmp)).returncode, 0)
        dest = self.tmp / "demo_ui"
        manifest = (dest / "fxmanifest.lua").read_text(encoding="utf-8")
        self.assertIn("ui_page 'web/dist/index.html'", manifest)
        self.assertTrue((dest / "web" / "package.json").exists())

    def test_rejects_bad_name(self):
        self.assertEqual(run("scaffold.py", "Bad Name", "--out", str(self.tmp)).returncode, 2)


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_and_links(self):
        skill = ROOT / "skills" / "fivem-development" / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: fivem-development\n"))
        desc = next(line for line in text.splitlines() if line.startswith("description:"))
        self.assertLessEqual(len(desc) - len("description: "), 1024)
        self.assertLess(len(text.splitlines()), 500)
        import re
        for link in re.findall(r"\]\((references/[^)#]+)", text):
            self.assertTrue((skill.parent / link).exists(), link)

    def test_plugin_json(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], market["plugins"][0]["name"])


if __name__ == "__main__":
    unittest.main()
