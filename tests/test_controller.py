"""Safety contracts: interrupted installs, concurrent writes, paths and backup contents."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('controller', Path(__file__).resolve().parents[1] / 'scripts/zephyrctl.py')
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        ctl.HOME = Path(self.temp.name)
        ctl.WORK = ctl.HOME / 'zephyr-work'
        ctl.STATE = ctl.HOME / 'state'
        self.app = ctl.WORK / 'zephyr4squirrels/apps/hello_world'
        self.app.mkdir(parents=True)
        (self.app / 'CMakeLists.txt').write_text('project(test)')

    def test_path_validation_rejects_escape_and_symlink(self):
        self.assertEqual(ctl.application('hello_world'), 'hello_world')
        for name in ('../outside', 'hello_world;id', 'hello world', '/tmp/a', 'absent'):
            with self.assertRaises(ValueError):
                ctl.application(name)
        (self.app.parent / 'outside').symlink_to(ctl.HOME, target_is_directory=True)
        with self.assertRaises(ValueError):
            ctl.application('outside')

    def test_interrupted_install_and_live_lock(self):
        ctl.write_state(phase='running', action='install')
        self.assertEqual(ctl.status()['phase'], 'interrupted')
        with (ctl.STATE / 'operation.lock').open('a') as lock:
            ctl.fcntl.flock(lock, ctl.fcntl.LOCK_EX)
            self.assertTrue(ctl.status()['busy'])
            self.assertEqual(ctl.status()['phase'], 'running')

    def test_resume_does_not_require_initial_download_space_again(self):
        # A completed Ubuntu download may already consume part of the original 12 GiB.
        with patch.object(ctl.shutil, 'disk_usage', return_value=SimpleNamespace(free=8 * 1024 ** 3)), \
             patch.object(ctl.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
             patch.object(ctl, 'guest') as guest:
            ctl.install()
            guest.assert_called_once()
        empty = ctl.HOME / 'fresh-work'
        with patch.object(ctl, 'WORK', empty), \
             patch.object(ctl.shutil, 'disk_usage', return_value=SimpleNamespace(free=8 * 1024 ** 3)), \
             patch.object(ctl.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            with self.assertRaises(RuntimeError):
                ctl.install()

    def test_backup_keeps_work_but_not_build_and_does_not_follow_links(self):
        course = self.app.parents[1]
        (course / 'build-hello_world').mkdir()
        (course / 'build-hello_world/large.bin').write_text('compiled')
        (course / '.git').mkdir()
        (course / '.git/HEAD').write_text('ref: refs/heads/moje-cviceni')
        (course / 'link').symlink_to(ctl.HOME / 'private.txt')
        (ctl.HOME / 'private.txt').write_text('not part of course')
        def guest(*args, **kwargs):
            # Use real GNU tar; replace only the guest mount point in this test.
            command = [str(ctl.WORK) + arg[5:] if arg == '/work' or arg.startswith('/work/') else arg for arg in args]
            subprocess.run(command, check=True, **kwargs)
        with patch.object(ctl, 'guest', guest):
            ctl.backup()
        with tarfile.open(next((ctl.HOME / 'zephyr-backups').glob('*.tar.gz'))) as archive:
            names = archive.getnames()
            self.assertIn('zephyr4squirrels/.git/HEAD', names)
            self.assertIn('zephyr4squirrels/apps/hello_world/CMakeLists.txt', names)
            self.assertFalse(any('large.bin' in name for name in names))
            self.assertTrue(archive.getmember('zephyr4squirrels/link').issym())


if __name__ == '__main__':
    unittest.main()
