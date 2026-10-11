import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'toolbox.py'


def load_toolbox():
    spec = importlib.util.spec_from_file_location('toolbox', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'toolbox.py is missing')
        self.toolbox = load_toolbox()

    def test_literal_arguments_and_exit_code_survive(self):
        arguments = ['中文 空格', 'https://example.com/?a=1&b=2', '%TEMP%', 'x > y', '"quoted"']
        provider = {'command': [sys.executable, '-c',
                    'import json,sys; print(json.dumps(sys.argv[1:],ensure_ascii=False)); sys.exit(7)'],
                    'env': {}}
        result = self.toolbox.execute(provider, arguments, capture=True)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(json.loads(result.stdout), arguments)

    def test_shell_entrypoints_are_rejected(self):
        with self.assertRaises(ValueError):
            self.toolbox.execute({'command': ['cmd.exe', '/c', 'echo'], 'env': {}}, ['hello'])

    def test_missing_provider_is_reported_missing(self):
        result = self.toolbox.inspect_provider({'command': ['Z:/not-installed/tool.exe']})
        self.assertEqual(result['installation'], 'missing')
        self.assertIsNone(result['resolved_executable'])

    def test_present_provider_is_reported_installed(self):
        result = self.toolbox.inspect_provider({'command': [sys.executable], 'version': '1'})
        self.assertEqual(result['installation'], 'installed')
        self.assertEqual(result['version'], '1')

    def test_eval_url_builds_a_fetch_in_page_context(self):
        request = self.toolbox.build_eval_request('webcli', url='https://example.com/api')
        self.assertEqual(request['command'][:2], ['browser', 'eval'])
        self.assertIn('credentials', request['command'][2])
        self.assertIn('https://example.com/api', request['command'][2])

    def test_eval_request_requires_code_or_url(self):
        with self.assertRaises(ValueError):
            self.toolbox.build_eval_request('webcli')

    def test_dont_write_bytecode_is_set(self):
        self.assertTrue(self.toolbox.sys.dont_write_bytecode)

    def test_upstream_update_preserves_local_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'SKILL.md'
            target.write_text('local change', encoding='utf-8')
            result = self.toolbox.sync_file(target, b'new upstream', b'old upstream', root / 'candidates')
            self.assertEqual(result, 'merge_required')
            self.assertEqual(target.read_text(encoding='utf-8'), 'local change')
            self.assertTrue((root / 'candidates' / 'SKILL.md').is_file())

    def test_unmodified_file_can_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'SKILL.md'
            target.write_bytes(b'old upstream')
            result = self.toolbox.sync_file(target, b'new upstream', b'old upstream', root / 'candidates')
            self.assertEqual(result, 'updated')
            self.assertEqual(target.read_bytes(), b'new upstream')

    def test_local_only_file_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'custom.md'
            target.write_bytes(b'local only')
            result = self.toolbox.sync_file(target, b'upstream has this name', None, root / 'candidates')
            self.assertEqual(result, 'merge_required')
            self.assertEqual(target.read_bytes(), b'local only')

    def test_config_round_trip_through_explicit_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'runtime.json'
            path.write_text(json.dumps({'providers': {'x': {'command': ['a']}}}), encoding='utf-8')
            config = self.toolbox.load_config(path)
            self.assertIn('x', config['providers'])

    def test_missing_config_raises_with_hint(self):
        with self.assertRaises(FileNotFoundError):
            self.toolbox.load_config(Path(tempfile.gettempdir()) / 'definitely-absent-runtime.json')


if __name__ == '__main__':
    unittest.main()
