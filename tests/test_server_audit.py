"""Whole-server audit tools: project.py, surface.py, data_file checks and the new audit.py rules.

The fixture tests/fixtures/server_project reproduces exploit classes and inventory facts that two
independent audits of a real server reported inconsistently; these tests keep them deterministic.
Run: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from test_scripts import FIX, run

SERVER = FIX / "server_project"


class SurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        res = run("surface.py", str(SERVER), "--json")
        cls.returncode = res.returncode
        cls.data = json.loads(res.stdout)
        cls.by_name = {e["name"]: e for e in cls.data["endpoints"]}

    def tags(self, name):
        return set(self.by_name[name]["tags"])

    def test_enumerates_every_entry_point_form(self):
        self.assertEqual(self.returncode, 0)
        expected = {"eco:job:payment", "eco:event:create", "eco:switchBucket", "eco:shop:buy", "eco:sell",
                    "eco:fuel:pay", "eco:broadcast", "eco_ok:buy"}
        self.assertEqual(expected, set(self.by_name))

    def test_exploit_class_tags(self):
        self.assertTrue({"credit-before-guard", "client-position"} <= self.tags("eco:job:payment"))
        self.assertIn("not-eq-precedence", self.tags("eco:event:create"))
        self.assertIn("client-value-in-sink", self.tags("eco:switchBucket"))
        self.assertTrue({"non-integer-amount", "no-balance-check"} <= self.tags("eco:shop:buy"))
        self.assertIn("unchecked-removal", self.tags("eco:sell"))
        self.assertTrue({"fanout", "no-source"} <= self.tags("eco:broadcast"))

    def test_follows_helpers_through_aliases(self):
        fuel = self.by_name["eco:fuel:pay"]
        self.assertIn("item-", fuel["sinks"])
        self.assertTrue(any("payMoney()" in s for s in fuel["sinks"]["item-"]))
        self.assertIn("client-value-in-sink", fuel["tags"])

    def test_validated_handler_has_no_exploit_tags(self):
        bad = {"non-integer-amount", "no-balance-check", "no-rate-limit", "credit-before-guard", "unchecked-removal"}
        self.assertEqual(self.tags("eco_ok:buy") & bad, set())

    def test_ids_are_stable(self):
        again = json.loads(run("surface.py", str(SERVER), "--json").stdout)
        self.assertEqual([(e["id"], e["name"]) for e in again["endpoints"]],
                         [(e["id"], e["name"]) for e in self.data["endpoints"]])

    def test_ledger_and_shards(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            ledger = tmp / "ledger.md"
            run("surface.py", str(SERVER), "--ledger", str(ledger))
            text = ledger.read_text(encoding="utf-8")
            self.assertEqual(text.count("| TODO |"), len(self.data["endpoints"]))
            names = set()
            for k in (1, 2):
                shard = json.loads(run("surface.py", str(SERVER), "--shard", f"{k}/2", "--json").stdout)
                names |= {e["name"] for e in shard["endpoints"]}
            self.assertEqual(names, set(self.by_name))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        res = run("project.py", str(SERVER), "--json", "--section", "cfg", "--section", "ensure",
                  "--section", "versions", "--section", "datafiles", "--section", "repo")
        cls.returncode = res.returncode
        cls.data = json.loads(res.stdout)
        cls.codes = {(f["severity"], f["code"]) for f in cls.data["findings"]}

    def test_exit_code_on_high(self):
        self.assertEqual(self.returncode, 1)

    def test_ensure_targets_that_do_not_exist(self):
        self.assertIn(("high", "ensure-missing-category"), self.codes)
        self.assertIn(("high", "ensure-missing-resource"), self.codes)

    def test_version_below_min_safe_with_citation(self):
        row = next(r for r in self.data["versions"] if r["resource"] == "oxmysql")
        self.assertEqual(row["status"], "< min-safe")
        self.assertTrue(row["where"].replace("\\", "/").endswith("oxmysql/fxmanifest.lua:7"))
        self.assertIn(("high", "version-below-min-safe"), self.codes)

    def test_cfg_facts(self):
        self.assertIn(("medium", "convar-conflict"), self.codes)
        self.assertIn(("low", "convar-removed"), self.codes)

    def test_bracket_folders_are_literal_in_data_files(self):
        self.assertEqual(self.data["broken_data_files"], 1)  # present.ytyp under stream/[props]/ resolves

    def test_script_referencing_missing_file(self):
        self.assertIn(("medium", "script-missing-target"), self.codes)


class ManifestDataFileTests(unittest.TestCase):
    def test_manifest_reports_missing_data_file_and_scans_folders(self):
        res = run("manifest.py", str(SERVER / "resources"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("1 of 2 data_file path(s) match no file", res.stdout)
        self.assertIn("missing.ytyp", res.stdout)
        self.assertNotIn("present.ytyp' ", res.stdout)
        self.assertIn("resource(s) checked", res.stdout)


class AuditNewRulesTests(unittest.TestCase):
    def test_not_eq_precedence_rule(self):
        rules = {f["rule"] for f in json.loads(run("audit.py", str(SERVER), "--json").stdout)}
        self.assertIn("lua-not-eq-precedence", rules)
        self.assertIn("client-reported-position", rules)


if __name__ == "__main__":
    unittest.main()
