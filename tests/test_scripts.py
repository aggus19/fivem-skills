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


class AuditIocRuleTests(unittest.TestCase):
    """New rule families: IOC/evasion lines, manifest concealment, cfg, dropper names, split events, package.json."""

    @classmethod
    def setUpClass(cls):
        cls.bad = [(f["severity"], f["rule"], f["file"].replace("\\", "/"))
                   for f in json.loads(run("audit.py", str(FIX / "ioc_resource"), "--json").stdout)]
        cls.clean = [f["rule"] for f in json.loads(run("audit.py", str(FIX / "clean_resource"), "--json").stdout)]

    def rules(self):
        return {r for _, r, _ in self.bad}

    def test_ioc_and_evasion_line_rules_match(self):
        expected = {"blum-xor-dropper", "known-backdoor-ext", "node-vm-run", "invoke-native-sensitive",
                    "hardcoded-discord-token", "txadmin-token-access", "env-index-evasion", "telegram-exfil",
                    "http-raw-ip", "io-open-write", "hardcoded-license-key", "client-sends-own-id",
                    "debug-lib-tamper", "resource-enumeration", "http-handler-public",
                    "statebag-handler-no-replicated", "lzstring-utf16", "nui-unsafe-html"}
        self.assertEqual(expected - self.rules(), set())

    def test_manifest_concealment_rules(self):
        self.assertIn(("critical", "manifest-hidden-injection", "fxmanifest.lua"), self.bad)
        self.assertIn(("high", "manifest-dotfile-js", "fxmanifest.lua"), self.bad)

    def test_cfg_rules(self):
        self.assertIn(("low", "cfg-nonexistent-devtools", "server.cfg"), self.bad)
        semis = [b for b in self.bad if b[1] == "cfg-unquoted-semicolon"]
        self.assertEqual(len(semis), 1)  # only the unquoted `;` line, not the quoted connection string

    def test_split_net_event_without_source(self):
        hits = [b for b in self.bad if b[1] == "net-event-no-source" and b[2].endswith("server/main.lua")]
        self.assertEqual(len(hits), 1)  # `source` appears only in a comment

    def test_dropper_names(self):
        self.assertIn(("critical", "known-backdoor", "server/sync_worker.js"), self.bad)  # name + loader code
        self.assertIn(("medium", "dropper-filename", "server/jest_mock.js"), self.bad)    # name only
        self.assertIn(("critical", "known-backdoor", "evil/yarn_builder.js"), self.bad)   # stock name, wrong place

    def test_package_json(self):
        self.assertIn(("medium", "npm-install-script", "package.json"), self.bad)
        self.assertIn(("medium", "npm-nonregistry-dep", "package.json"), self.bad)

    def test_benign_lookalikes_not_flagged(self):
        # clean_resource only legitimately trips convar-secret (reading sv_licenseKey via GetConvar)
        self.assertEqual(set(self.clean), {"convar-secret"}, self.clean)


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
