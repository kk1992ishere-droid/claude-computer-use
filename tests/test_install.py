"""Configuration-only tests: no live MCP server or user config is touched."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'install.py'


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, 'HOME': str(self.root), 'CODEX_HOME': str(self.root / 'codex')}
        self.source = self.root / 'source.json'
        self.source.write_text(json.dumps({'mcpServers': {'cua_repl': {
            'command': '/not/executed/node', 'args': ['path with spaces/main.js'],
            'env': {'KEEP': 'value', 'NODE_REPL_DISABLE_ANALYTICS': '0'}}}}))
        self.config = self.root / 'client.json'

    def run_cli(self, *args, ok=True, source=True):
        cmd = [sys.executable, str(SCRIPT)]
        if source:
            cmd += ['--source', str(self.source)]
        result = subprocess.run(cmd + list(args), env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result

    def test_export_does_not_install_or_launch(self):
        data = json.loads(self.run_cli().stdout)
        self.assertEqual(data['args'], ['path with spaces/main.js'])
        self.assertEqual(data['env']['KEEP'], 'value')
        self.assertEqual(data['env']['NODE_REPL_DISABLE_ANALYTICS'], '1')
        self.assertNotIn('type', data)
        self.assertFalse((self.root / '.claude.json').exists())

    def test_preview_merge_backup_idempotence_and_uninstall(self):
        original = {'private': 'do-not-print', 'nested': {'servers': {'other': {'command': 'keep'}}}}
        self.config.write_text(json.dumps(original))
        flags = ['--config', str(self.config), '--section', 'nested', 'servers', '--stdio-type']
        preview = self.run_cli(*flags)
        self.assertNotIn('do-not-print', preview.stdout)
        self.assertEqual(json.loads(self.config.read_text()), original)
        self.run_cli(*flags, '--apply')
        data = json.loads(self.config.read_text())
        self.assertEqual(data['nested']['servers']['other'], {'command': 'keep'})
        self.assertEqual(data['nested']['servers']['ccu']['type'], 'stdio')
        self.assertEqual(data['private'], original['private'])
        backups = list(self.root.glob('client.json.bak-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text()), original)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        self.run_cli(*flags, '--apply')
        self.assertEqual(len(list(self.root.glob('client.json.bak-*'))), 1)
        self.source.unlink()
        self.run_cli(*flags, '--uninstall', '--apply', source=False)
        self.assertEqual(json.loads(self.config.read_text()), original)

    def test_conflict_requires_explicit_replace(self):
        self.config.write_text('{"mcpServers":{"ccu":{"command":"existing"}}}')
        flags = ['--config', str(self.config), '--apply']
        self.run_cli(*flags, ok=False)
        self.assertEqual(json.loads(self.config.read_text())['mcpServers']['ccu']['command'], 'existing')
        self.run_cli(*flags, '--replace')
        self.assertEqual(json.loads(self.config.read_text())['mcpServers']['ccu']['command'], '/not/executed/node')

    def test_invalid_configs_remain_untouched(self):
        for content in ['// JSONC\n{}', '[mcp_servers]', '{"mcpServers":[]}', '[]']:
            self.config.write_text(content)
            self.run_cli('--config', str(self.config), '--apply', ok=False)
            self.assertEqual(self.config.read_text(), content)

    def test_generic_does_not_accept_claude_hooks(self):
        self.run_cli('--config', str(self.config), '--auto-approve', '--apply', ok=False)
        self.run_cli('--uninstall', '--apply', ok=False)
        self.assertFalse(self.config.exists())
        self.assertFalse((self.root / '.claude').exists())

    def test_discovery_uses_codex_home_and_newest_version(self):
        for version in ['1.9.0', '1.10.0']:
            source = Path(self.env['CODEX_HOME']) / 'plugins/cache/openai-bundled/unified-computer-use' / version / '.mcp.json'
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({'mcpServers': {'cua_repl': {'command': version}}}))
        self.assertEqual(json.loads(self.run_cli(source=False).stdout)['command'], '1.10.0')

    def test_claude_preview_and_explicit_adapter(self):
        self.run_cli('--client', 'claude')
        self.assertFalse((self.root / '.claude.json').exists())
        # Hide the real Claude CLI: exercise the isolated file fallback only.
        self.env['PATH'] = str(self.root)
        self.run_cli('--client', 'claude', '--apply')
        data = json.loads((self.root / '.claude.json').read_text())
        self.assertEqual(data['mcpServers']['ccu']['type'], 'stdio')
        self.assertFalse((self.root / '.claude/hooks/ccu-approve.py').exists())
        self.run_cli('--client', 'claude', '--auto-approve', '--apply')
        self.assertTrue((self.root / '.claude/hooks/ccu-approve.py').exists())
        self.run_cli('--client', 'claude', '--uninstall', '--apply', source=False)
        self.assertNotIn('ccu', json.loads((self.root / '.claude.json').read_text())['mcpServers'])
        self.assertFalse((self.root / '.claude/hooks/ccu-approve.py').exists())

    def test_symlink_is_not_replaced(self):
        real = self.root / 'real.json'
        real.write_text('{}')
        self.config.symlink_to(real)
        self.run_cli('--config', str(self.config), '--apply', ok=False)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(real.read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
