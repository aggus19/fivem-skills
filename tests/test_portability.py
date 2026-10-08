"""The skill must work on any server: any framework, any layout, run from inside resources/, any console encoding.

Run: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from test_scripts import FIX, run

MULTI = FIX / "multi_framework"
SERVER = FIX / "server_project"


class MultiFrameworkSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(run("surface.py", str(MULTI), "--json").stdout)
        cls.by_name = {e["name"]: e for e in cls.data["endpoints"]}

    def test_qbcore_callback_and_command(self):
        buy = self.by_name["qb_shop:buy"]
        self.assertEqual(buy["kind"], "callback")
        self.assertTrue({"money-", "item+"} <= set(buy["sinks"]))
        self.assertTrue({"non-integer-amount", "no-balance-check"} <= set(buy["tags"]))
        self.assertEqual(self.by_name["givecash"]["kind"], "command")

    def test_vrp_tunnel_methods_are_endpoints(self):
        sell = self.by_name["vrp_garage.sellVehicle"]
        self.assertEqual(sell["kind"], "tunnel")
        self.assertIn("money+", sell["sinks"])
        self.assertIn("client-value-in-sink", sell["tags"])
        self.assertTrue(all("via sellVehicle()" not in s for s in sell["sinks"]["money+"]))
        self.assertIn("vrp_garage.vehicleList", self.by_name)


class LayoutAndStackTests(unittest.TestCase):
    def test_runs_from_inside_a_resources_subfolder(self):
        res = run("project.py", str(MULTI / "resources" / "[qb]"), "--json", "--section", "stack")
        data = json.loads(res.stdout)
        self.assertEqual(Path(data["root"]).resolve(), MULTI.resolve())
        names = {r["name"] for r in data["stack"]}
        self.assertTrue({"QBCore", "vRP / Creative"} <= names)
        self.assertIn("framework-multiple", {f["code"] for f in data["findings"]})

    def test_txadmin_cfgpath_is_the_launch_cfg(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            server = tmp / "server-data"
            shutil.copytree(str(SERVER), str(server))
            (server / "dev.cfg").write_text("ensure oxmysql\nensure [eco]\n", encoding="utf-8")
            profile = tmp / "txData" / "default"
            profile.mkdir(parents=True)
            (profile / "config.json").write_text(json.dumps({"server": {"dataPath": str(server), "cfgPath": "dev.cfg"}}),
                                                 encoding="utf-8")
            data = json.loads(run("project.py", str(server / "resources"), "--json", "--section", "cfg",
                                  "--section", "ensure").stdout)
            self.assertTrue(data["launch_cfg"].endswith("dev.cfg"))
            launch = [f for f in data["findings"] if f["code"] == "launch-cfg"]
            self.assertIn("txAdmin cfgPath", launch[0]["message"])
            not_execd = {f["where"] for f in data["findings"] if f["code"] == "cfg-not-execd"}
            self.assertIn("server.cfg", not_execd)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scripts_default_to_current_directory(self):
        cwd = os.getcwd()
        try:
            os.chdir(str(MULTI / "resources"))
            self.assertEqual(run("surface.py").returncode, 0)
            self.assertIn("qb_shop", run("manifest.py").stdout)
        finally:
            os.chdir(cwd)


class LogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        res = run("logs.py", str(MULTI), "--json")
        cls.returncode = res.returncode
        cls.data = json.loads(res.stdout)
        cls.codes = {}
        for item in cls.data["items"]:
            cls.codes.setdefault(item["code"], []).append(item)

    def test_finds_the_log_and_sessions(self):
        self.assertEqual(self.returncode, 0)
        self.assertEqual(self.data["sessions"], 2)

    def test_groups(self):
        err = self.codes["script-error"][0]
        self.assertEqual(err["count"], 2)
        self.assertIn("qb_shop/server.lua:5", err["key"])
        self.assertEqual(err["extra"]["frame"], "qb_shop/server.lua:5 (fn)")
        for code in ("error-loading-script", "category-not-found", "escrow-entitlement", "resource-not-started",
                     "slow-query", "oversized-result", "asset-memory", "convar-removed", "exec-missing",
                     "argument-count", "statebag-strict-off", "process-close"):
            self.assertIn(code, self.codes, code)
        hitch = {i["key"]: i for i in self.codes["thread-hitch"]}
        self.assertEqual(hitch["server thread"]["max"], 1290)
        self.assertEqual(hitch["server thread"]["count"], 2)

    def test_secrets_are_masked(self):
        text = json.dumps(self.data)
        self.assertNotIn("cfxk_abcdefghijklmnopqrstuvwxyz0123456789", text)
        self.assertIn("secret-in-log", self.codes)

    def test_last_session_only(self):
        data = json.loads(run("logs.py", str(MULTI / "logs" / "fxserver.log"), "--json", "--last").stdout)
        codes = {i["code"] for i in data["items"]}
        self.assertIn("thread-hitch", codes)
        self.assertNotIn("script-error", codes)


class GeneratedCodeCommentTests(unittest.TestCase):
    def test_scaffold_ships_lua_without_comments(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            res = run("scaffold.py", "demo_res", "--out", str(tmp), "--profile", "ox-shop")
            self.assertEqual(res.returncode, 0, res.stderr)
            for lua in (tmp / "demo_res").rglob("*.lua"):
                if lua.name == "fxmanifest.lua":
                    continue
                text = lua.read_text(encoding="utf-8")
                code = [l for l in text.splitlines() if l.strip().startswith("--")]
                self.assertEqual(code, [], lua.name)
            kept = Path(tempfile.mkdtemp())
            run("scaffold.py", "demo_res", "--out", str(kept), "--profile", "ox-shop", "--keep-comments")
            self.assertIn("--", (kept / "demo_res" / "server" / "main.lua").read_text(encoding="utf-8"))
            shutil.rmtree(kept, ignore_errors=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ConsoleEncodingTests(unittest.TestCase):
    def test_non_utf8_console_does_not_crash(self):
        env = {"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        for script, args in (("logs.py", [str(MULTI)]), ("project.py", [str(SERVER)]), ("surface.py", [str(SERVER)]),
                             ("audit.py", [str(SERVER)]), ("manifest.py", [str(SERVER / "resources")])):
            res = run(script, *args, env=env)
            self.assertNotIn("UnicodeEncodeError", res.stderr, script)
            self.assertIn(res.returncode, (0, 1), script)


if __name__ == "__main__":
    unittest.main()
