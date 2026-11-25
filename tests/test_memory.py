import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'memory_tool.py'

class MemoryTests(unittest.TestCase):
    def test_commands_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'sessions').mkdir()
            (root / 'projects').mkdir()
            (root / 'lessons.md').write_text('- 2026-01-01 | demo | #подряд | Ёлка → вывод → причина\n', encoding='utf-8')
            (root / 'sessions' / '2026-01-01_demo.md').write_text('# Сессия', encoding='utf-8')
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            def run(*args):
                return json.loads(subprocess.check_output([sys.executable, '-X', 'utf8', str(SCRIPT), args[0], str(root), *args[1:], '--json'], encoding='utf-8'))
            self.assertIsInstance(run('status'), dict)
            self.assertEqual(len(run('recall', 'елка')['уроки']), 1)
            self.assertEqual(run('lessons', '--tags', '#подряд')['уроков'], 1)
            self.assertEqual(run('lessons', '--exclude-case', 'demo')['уроков'], 0)
            self.assertEqual(run('nextname', 'demo', '--date', '2026-01-01')['файл'], 'sessions/2026-01-01_demo-2.md')
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()})
