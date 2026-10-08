"""Opt-in real template build. Needs Bun and registry/cache access, not FXServer."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_scripts import run


@unittest.skipUnless(os.environ.get('FIVEM_TEST_NUI_BUILD') == '1', 'set FIVEM_TEST_NUI_BUILD=1 for the Bun build')
class NuiBuildTests(unittest.TestCase):
    def test_generated_nui_builds_with_frozen_lock_and_manifest_covers_output(self):
        self.build_profile('minimal')

    def test_explicit_shop_nui_builds_and_manifest_covers_output(self):
        self.build_profile('ox-shop')

    def build_profile(self, profile):
        bun = shutil.which('bun')
        self.assertIsNotNone(bun, 'Bun must be installed for the requested build test')
        with tempfile.TemporaryDirectory(prefix='fivem-nui-test-') as tmp:
            created = run('scaffold.py', 'test_ui', '--profile', profile, '--nui', '--out', tmp)
            self.assertEqual(created.returncode, 0, created.stderr)
            resource = Path(tmp) / 'test_ui'
            web = resource / 'web'
            lock = (web / 'bun.lock').read_bytes()
            for args in (['install', '--frozen-lockfile'], ['run', '--bun', 'build']):
                result = subprocess.run([bun, *args], cwd=str(web), capture_output=True, text=True,
                                        encoding='utf-8', timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((web / 'bun.lock').read_bytes(), lock)
            self.assertTrue((web / 'dist/index.html').is_file())
            manifest = run('manifest.py', str(resource))
            self.assertEqual(manifest.returncode, 0, manifest.stdout + manifest.stderr)


if __name__ == '__main__':
    unittest.main()
