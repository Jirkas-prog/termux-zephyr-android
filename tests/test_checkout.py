import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('setup', Path(__file__).resolve().parents[1] / 'scripts/linux-setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class CheckoutTest(unittest.TestCase):
    def test_commits_origins_and_validation_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            setup.ROOT = root
            remote = root / 'remote'
            remote.mkdir()
            def git(path, *args):
                return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()
            git(remote, 'init')
            git(remote, 'config', 'user.name', 'Test')
            git(remote, 'config', 'user.email', 'test@example.invalid')
            (remote / 'apps/hello_world/src').mkdir(parents=True)
            (remote / 'scripts').mkdir()
            (remote / 'apps/hello_world/src/main.c').write_text('original')
            (remote / 'scripts/run-qemu.sh').write_text('#!/bin/sh\n')
            git(remote, 'add', '.'); git(remote, 'commit', '-m', 'Original')
            first = git(remote, 'rev-parse', 'HEAD')
            git(remote, 'tag', 'v1')
            course = root / 'course'
            setup.checkout(course, str(remote), first, 'moje-cviceni')
            git(course, 'config', 'user.name', 'Test')
            git(course, 'config', 'user.email', 'test@example.invalid')
            (course / 'apps/hello_world/src/main.c').write_text('student commit')
            git(course, 'commit', '-am', 'My exercise')
            student = git(course, 'rev-parse', 'HEAD')
            (course / 'apps/hello_world/src/main.c').write_text('unfinished student edits')
            setup.checkout(course, str(remote), first, 'moje-cviceni')
            self.assertEqual(git(course, 'rev-parse', 'HEAD'), student)
            old_revision = setup.CONFIG['course_revision']
            try:
                setup.CONFIG['course_revision'] = first
                sample = setup.validation_source(course)
                self.assertEqual((sample / 'apps/hello_world/src/main.c').read_text(), 'original')
                self.assertEqual((course / 'apps/hello_world/src/main.c').read_text(), 'unfinished student edits')
            finally:
                setup.CONFIG['course_revision'] = old_revision
            (remote / 'new.txt').write_text('new upstream')
            git(remote, 'add', '.'); git(remote, 'commit', '-m', 'Upstream change')
            second = git(remote, 'rev-parse', 'HEAD')
            zephyr = root / 'zephyr'
            setup.checkout(zephyr, str(remote), first)
            git(zephyr, 'config', 'user.name', 'Test')
            git(zephyr, 'config', 'user.email', 'test@example.invalid')
            (zephyr / 'my.txt').write_text('private commit')
            git(zephyr, 'add', '.'); git(zephyr, 'commit', '-m', 'Custom changes')
            custom = git(zephyr, 'rev-parse', 'HEAD')
            # A manually cloned module has no manifest-rev; its commits are still private work.
            with self.assertRaisesRegex(RuntimeError, 'commity'):
                setup.protect_module(zephyr)
            git(zephyr, 'update-ref', 'refs/heads/manifest-rev', custom)
            setup.protect_module(zephyr)
            with self.assertRaisesRegex(RuntimeError, 'commity'):
                setup.checkout(zephyr, str(remote), second)
            self.assertEqual(git(zephyr, 'rev-parse', 'HEAD'), custom)
            with self.assertRaisesRegex(RuntimeError, 'origin'):
                setup.checkout(course, str(root / 'other'), first)
            self.assertEqual(git(course, 'rev-parse', 'HEAD'), student)
            # Migrate v1.0.1 clones with no managed base ref or local tag.
            legacy = root / 'legacy'
            setup.checkout(legacy, str(remote), first)
            git(legacy, 'update-ref', '-d', 'refs/zephyr-manager/base')
            setup.checkout(legacy, str(remote), second, previous_revision='v1')
            self.assertEqual(git(legacy, 'rev-parse', 'HEAD'), second)
            interrupted_module = root / 'interrupted-module'
            interrupted_module.mkdir()
            git(interrupted_module, 'init')
            setup.protect_module(interrupted_module)

    def test_fresh_clone_resume_and_student_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            setup.ROOT = root
            remote = root / 'remote'
            subprocess.run(['git', 'init', str(remote)], check=True, capture_output=True)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(remote), *args], text=True).strip()
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            (remote / 'source.c').write_text('v1')
            (remote / 'src').mkdir(); (remote / 'src/example.c').write_text('code')
            (remote / 'doc').mkdir(); (remote / 'doc/example.txt').write_text('docs')
            git('add', '.'); git('commit', '-m', 'First')
            first = git('rev-parse', 'HEAD')
            target = root / 'course'
            setup.checkout(target, str(remote), first, 'moje-cviceni')
            self.assertEqual((target / 'source.c').read_text(), 'v1')
            (target / 'source.c').write_text('student work')
            setup.checkout(target, str(remote), first, 'moje-cviceni')
            self.assertEqual((target / 'source.c').read_text(), 'student work')
            (remote / 'source.c').write_text('v2')
            git('commit', '-am', 'Second')
            second = git('rev-parse', 'HEAD')
            with self.assertRaises(RuntimeError):
                setup.checkout(target, str(remote), second, 'moje-cviceni')
            self.assertEqual((target / 'source.c').read_text(), 'student work')
            (target / 'source.c').write_text('v1')
            setup.checkout(target, str(remote), second, 'moje-cviceni')
            self.assertEqual((target / 'source.c').read_text(), 'v2')
            # Initialised but interrupted before fetch: the next attempt must recover.
            interrupted = root / 'interrupted'
            subprocess.run(['git', 'init', str(interrupted)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(interrupted), 'remote', 'add', 'origin', str(remote)], check=True)
            setup.checkout(interrupted, str(remote), first)
            self.assertEqual((interrupted / 'source.c').read_text(), 'v1')
            partial = root / 'partial'
            setup.checkout(partial, str(remote), first, sparse=True)
            self.assertFalse((partial / 'doc').exists())
            subprocess.run(['git', '-C', str(partial), 'sparse-checkout', 'add', 'src'], check=True)
            self.assertEqual((partial / 'src/example.c').read_text(), 'code')
            subprocess.run(['git', '-C', str(partial), 'sparse-checkout', 'disable'], check=True)
            setup.checkout(partial, str(remote), first, sparse=True)
            self.assertTrue((partial / 'doc/example.txt').exists())
            self.assertEqual(subprocess.check_output(['git', '-C', str(partial), 'config', '--get', 'core.sparseCheckout'], text=True).strip(), 'false')


if __name__ == '__main__':
    unittest.main()
