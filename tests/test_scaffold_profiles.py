"""Observable profile, relocation and overwrite boundaries; no FXServer required."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_scripts import SCRIPTS, run


class ScaffoldProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fivem profiles ')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_resource_needs_no_framework_database_or_network_handler(self):
        result = run('scaffold.py', 'plain_feature', '--out', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.root / 'plain_feature'
        manifest = (dest / 'fxmanifest.lua').read_text()
        self.assertNotIn('dependenc', manifest)
        self.assertNotIn('@', manifest)
        self.assertFalse((dest / 'bridge').exists())
        for p in dest.rglob('*.lua'):
            executable = '\n'.join(line for line in p.read_text().splitlines()
                                   if not line.lstrip().startswith('--'))
            self.assertNotIn('RegisterNetEvent', executable)
            self.assertNotIn('MySQL.', executable)
        self.assertEqual(run('manifest.py', str(dest)).returncode, 0)
        self.assertEqual(run('audit.py', str(dest)).returncode, 0)

    def test_explicit_shop_retains_disabled_integration_and_valid_manifest(self):
        result = run('scaffold.py', 'shop_feature', '--profile', 'ox-shop', '--out', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.root / 'shop_feature'
        self.assertTrue((dest / 'bridge/init.lua').is_file())
        self.assertTrue((dest / 'server/purchase.lua').is_file())
        self.assertIn('PurchasesEnabled = false', (dest / 'config/server.lua').read_text())
        self.assertEqual(run('manifest.py', str(dest)).returncode, 0)
        audit = run('audit.py', str(dest), '--min', 'high')
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)

    def test_unknown_profile_creates_no_output(self):
        result = run('scaffold.py', 'bad_profile', '--profile', 'unknown', '--out', str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_relocated_skill_works_from_unrelated_project_directory(self):
        installed = self.root / 'project/.agents/skills/fivem-development'
        (installed / 'scripts').mkdir(parents=True)
        shutil.copy2(SCRIPTS / 'scaffold.py', installed / 'scripts/scaffold.py')
        shutil.copytree(SCRIPTS.parent / 'assets/templates/resource-minimal',
                        installed / 'assets/templates/resource-minimal')
        project = self.root / 'another project'
        project.mkdir()
        result = subprocess.run([sys.executable, '-I', str(installed / 'scripts/scaffold.py'),
                                 'local_feature', '--out', 'resources'], cwd=str(project),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / 'resources/local_feature/fxmanifest.lua').is_file())
        self.assertFalse((installed / 'resources').exists())

    def test_existing_directory_is_preserved_without_force(self):
        target = self.root / 'existing'
        target.mkdir()
        sentinel = target / 'user-data.txt'
        sentinel.write_text('preserve')
        result = run('scaffold.py', 'existing', '--out', str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(sentinel.read_text(), 'preserve')

    def test_force_replaces_only_verified_child_directory(self):
        target = self.root / 'replace_me'
        target.mkdir()
        (target / 'old.txt').write_text('old')
        sibling = self.root / 'keep.txt'
        sibling.write_text('keep')
        result = run('scaffold.py', 'replace_me', '--out', str(self.root), '--force')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((target / 'old.txt').exists())
        self.assertTrue((target / 'fxmanifest.lua').exists())
        self.assertEqual(sibling.read_text(), 'keep')

    def test_force_does_not_follow_resource_directory_link(self):
        with tempfile.TemporaryDirectory(prefix='fivem external ') as outside:
            target = Path(outside)
            sentinel = target / 'keep.txt'
            sentinel.write_text('keep')
            try:
                (self.root / 'linked').symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest('directory symlink unavailable: {}'.format(exc))
            result = run('scaffold.py', 'linked', '--out', str(self.root), '--force')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(sentinel.read_text(), 'keep')
            self.assertEqual(list(target.iterdir()), [sentinel])

    def test_force_rejects_a_file_without_removing_it(self):
        target = self.root / 'a_file'
        target.write_text('keep')
        result = run('scaffold.py', 'a_file', '--out', str(self.root), '--force')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(target.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
