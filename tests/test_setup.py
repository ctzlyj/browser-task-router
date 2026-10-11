import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'setup.py'


def load_setup():
    spec = importlib.util.spec_from_file_location('setup_module', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'setup.py is missing')
        self.setup = load_setup()

    def test_merge_adds_without_touching_others(self):
        existing = {'format_version': 'v1', 'clis': [{'name': 'keep', 'entry_point': ['safe.exe']}], 'custom': True}
        merged, added = self.setup.merge_registry(existing, [{'name': 'new', 'entry_point': ['new.exe']}])
        self.assertEqual(existing['clis'], [{'name': 'keep', 'entry_point': ['safe.exe']}])
        self.assertEqual(merged['clis'][0]['name'], 'keep')
        self.assertTrue(merged['custom'])
        self.assertEqual(added, ['new'])

    def test_existing_entry_with_different_entrypoint_is_preserved(self):
        existing = {'clis': [{'name': 'webcli-local', 'entry_point': ['node', 'other.js']}]}
        merged, added = self.setup.merge_registry(
            existing, [{'name': 'webcli-local', 'entry_point': ['python', 'toolbox.py']}])
        self.assertEqual(merged['clis'][0]['entry_point'], ['node', 'other.js'])
        self.assertEqual(added, [])

    def test_aliases_include_the_toolbox_entry_and_each_provider(self):
        providers = {'webcli': {'kind': 'browser-context', 'guide': 'references/webcli.md'}}
        aliases = self.setup.build_aliases(providers)
        names = [entry['name'] for entry in aliases]
        self.assertIn('browser-toolbox-local', names)
        self.assertIn('webcli-local', names)

    def test_extra_roots_come_from_the_environment(self):
        sentinel = str(Path(tempfile.gettempdir()) / 'btr-sentinel-tools')
        previous = os.environ.get('BROWSER_TOOLBOX_ROOTS')
        os.environ['BROWSER_TOOLBOX_ROOTS'] = sentinel
        try:
            self.assertIn(sentinel, self.setup.default_roots())
        finally:
            if previous is None:
                os.environ.pop('BROWSER_TOOLBOX_ROOTS', None)
            else:
                os.environ['BROWSER_TOOLBOX_ROOTS'] = previous

    def test_setup_writes_a_usable_config(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'runtime.json'
            code = self.setup.main(['--config', str(target), '--no-registry'])
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            config = json.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(config['format_version'], 'browser-task-router/v1')

    def test_setup_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'runtime.json'
            target.write_text('{}', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                self.setup.main(['--config', str(target), '--no-registry'])


if __name__ == '__main__':
    unittest.main()
