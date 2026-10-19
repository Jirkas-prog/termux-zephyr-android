import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('setup', Path(__file__).resolve().parents[1] / 'scripts/linux-setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class CheckoutTest(unittest.TestCase):
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
