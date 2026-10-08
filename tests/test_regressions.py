"""Reproductions from the skill review; offline, standard-library tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_scripts import FIX, SCRIPTS, run

sys.path.insert(0, str(SCRIPTS))
from resource_files import ManifestError, parse_manifest


class ResourceRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('fxmanifest.lua', "fx_version 'cerulean'\ngame 'gta5'\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def manifest(self, extra):
        self.write('fxmanifest.lua', "fx_version 'cerulean'\ngame 'gta5'\n" + extra)

    def native_check(self, *paths):
        return run('natives.py', 'check', *(str(p) for p in (paths or (self.root,))), '--strict',
                   env={'FIVEM_SKILL_CACHE': str(FIX / 'natives_cache')})

    def test_native_missing_path_fails_before_cache_lookup(self):
        self.assertEqual(self.native_check(self.root / 'absent').returncode, 2)

    def test_native_empty_input_fails(self):
        empty = self.root / 'empty'
        empty.mkdir()
        self.assertEqual(self.native_check(empty).returncode, 2)

    def test_native_manifest_side_beats_filename(self):
        self.manifest("server_script('main.lua')")
        self.write('main.lua', 'local ped = PlayerPedId()')
        result = self.native_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('WRONG-SIDE', result.stdout)

    def test_native_shared_file_checks_both_runtimes(self):
        self.manifest("shared_scripts {'common/*.lua'}")
        self.write('common/data.lua', 'local ped = PlayerPedId()')
        self.assertIn('unavailable on server', self.native_check().stdout)

    def test_native_both_script_lists_check_both_runtimes(self):
        self.manifest("client_script 'main.lua'\nserver_script 'main.lua'")
        self.write('main.lua', 'local ped = PlayerPedId()')
        self.assertEqual(self.native_check().returncode, 1)

    def test_native_comments_and_long_strings_are_not_calls(self):
        self.manifest("server_script 'main.lua'")
        self.write('main.lua', "--[=[\nPlayerPedId()\n]=]\nlocal text = [==[PlayerPedId()]==]\nlocal x = '--'; PlayerPedId()")
        result = self.native_check()
        self.assertEqual(result.stdout.count('WRONG-SIDE'), 1, result.stdout)
        self.assertIn(':5:', result.stdout)

    def test_computed_manifest_never_silently_passes(self):
        self.manifest("local p = 'main.lua'\nserver_script(p)")
        self.write('main.lua', 'local ped = PlayerPedId()')
        self.assertEqual(run('manifest.py', str(self.root)).returncode, 1)
        self.assertIn('UNRESOLVED-MANIFEST', self.native_check().stdout)

    def test_glob_resolves_server_files_before_exposure_check(self):
        self.manifest("shared_scripts {'**.lua'}")
        self.write('server/secrets.lua', "local secret = 'fixture'")
        result = run('manifest.py', str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn('server/secrets.lua', result.stdout)

    def test_downloads_expose_neutrally_named_server_script(self):
        self.manifest("server_script 'logic.lua'\nfiles {'*.lua'}")
        self.write('logic.lua', 'local value = 1')
        self.assertIn("exposes server file 'logic.lua'", run('manifest.py', str(self.root)).stdout)

    def test_server_only_resource_does_not_download_files(self):
        self.manifest("server_only 'yes'\nserver_script 'server/main.lua'\nfiles {'server/*.lua'}")
        self.write('server/main.lua', 'local value = 1')
        self.assertEqual(run('manifest.py', str(self.root)).returncode, 0)

    def test_manifest_external_paths_report_error_without_traceback(self):
        for pattern in ('../other.lua', '/absolute.lua', 'C:/absolute.lua'):
            with self.subTest(pattern=pattern):
                self.manifest("server_script '%s'" % pattern)
                result = run('manifest.py', str(self.root))
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)

    def test_audit_single_file_matches_directory_finding(self):
        path = self.write('server/main.lua', 'local fn = load(payload)')
        for target in (path, path.parent):
            result = run('audit.py', str(target), '--json')
            self.assertEqual(result.returncode, 1)
            self.assertIn('rce-load', {f['rule'] for f in json.loads(result.stdout)})

    def test_audit_filter_does_not_suppress_failure_status(self):
        path = self.write('server/main.lua', 'local fn = load(payload)')
        result = run('audit.py', str(path), '--min', 'critical', '--json')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertIn('hidden by --min', result.stderr)

    def test_audit_scans_shipped_code_in_build_directories(self):
        for folder in ('dist', 'build', 'stream', '.next'):
            with self.subTest(folder=folder):
                path = self.write(folder + '/entry.js', 'eval(payload);')
                self.manifest("server_script '%s/entry.js'" % folder)
                result = run('audit.py', str(self.root), '--json')
                self.assertEqual(result.returncode, 1)
                self.assertTrue(any(f['file'].replace('\\', '/') == folder + '/entry.js'
                                    for f in json.loads(result.stdout)))
                path.unlink()

    def test_audit_neutral_filename_uses_manifest_side(self):
        self.manifest("client_script 'main.lua'")
        self.write('main.lua', "local hook = 'https://discord.com/api/webhooks/123/example'")
        result = run('audit.py', str(self.root), '--json')
        self.assertIn('webhook-exposed', {f['rule'] for f in json.loads(result.stdout)})

    def test_audit_empty_input_is_not_clean(self):
        self.assertEqual(run('audit.py', str(self.write('ignored.txt', 'text'))).returncode, 2)

    def test_scaffold_escapes_lua_metadata(self):
        author = "O'Connor\\team\nline -- kept"
        result = run('scaffold.py', 'quoted', '--out', str(self.root), '--author', author)
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.root / 'quoted'
        parsed = parse_manifest((dest / 'fxmanifest.lua').read_text(encoding='utf-8'))
        self.assertEqual(parsed['author'], [author])
        self.assertEqual(run('manifest.py', str(dest)).returncode, 0)


class LiteralManifestTests(unittest.TestCase):
    def test_comments_long_strings_parentheses_and_extras(self):
        data = parse_manifest("""--[=[ ignored client_script 'bad.lua' ]=]
fx_version('cerulean')
author 'A -- B'
description [==[quoted ' and -- text]==]
server_scripts({ 'main.lua'; 'extra.lua', })
my_data('nine')({ninety = 'nein'})
data_file 'TYPE' 'data/file.meta'
""")
        self.assertEqual(data['author'], ['A -- B'])
        self.assertEqual(data['server_scripts'], ['main.lua', 'extra.lua'])
        self.assertNotIn('client_script', data)
        self.assertEqual(data['my_data'], ['nine'])

    def test_malformed_and_computed_lists_are_explicitly_unsupported(self):
        for text in ("author 'O'Connor'", "files {'a' 'b'}", "files { prefix .. '/a.lua' }",
                     "files {'x'", "files { 'a' } .. suffix", "server_script `adder`"):
            with self.subTest(text=text), self.assertRaises(ManifestError):
                parse_manifest(text)


if __name__ == '__main__':
    unittest.main()
