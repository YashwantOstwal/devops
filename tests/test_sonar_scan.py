"""Exercise release-blocking behavior without needing a SonarQube server."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'sonar-scan.sh'


class SonarScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = self.root / 'target/site/jacoco/jacoco.xml'
        self.report.parent.mkdir(parents=True)
        self.report.write_text('<report/>')
        binary = self.root / 'mvn'
        binary.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > arguments\nexit "${SCANNER_EXIT:-0}"\n')
        binary.chmod(0o755)
        self.env = {**os.environ, 'PATH': f'{self.root}:{os.environ["PATH"]}',
                    'SONAR_TOKEN': 'test-token-never-print',
                    'SONAR_HOST_URL': 'https://sonar.example.test',
                    'SONAR_PROJECT_KEY': 'demo', 'SONAR_ORGANIZATION': ''}

    def run_scan(self):
        return subprocess.run(['bash', str(SCRIPT)], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def test_missing_configuration_blocks_scanner(self):
        for key in ('SONAR_TOKEN', 'SONAR_HOST_URL', 'SONAR_PROJECT_KEY'):
            with self.subTest(key=key):
                value = self.env.pop(key)
                result = self.run_scan()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)
                self.assertFalse((self.root / 'arguments').exists())
                self.env[key] = value

    def test_missing_coverage_blocks_scanner(self):
        self.report.unlink()
        self.assertNotEqual(self.run_scan().returncode, 0)
        self.assertFalse((self.root / 'arguments').exists())

    def test_passing_gate_succeeds_and_waits(self):
        result = self.run_scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        arguments = (self.root / 'arguments').read_text()
        self.assertIn('-Dsonar.qualitygate.wait=true\n', arguments)
        self.assertIn('-Dsonar.qualitygate.timeout=300\n', arguments)
        self.assertNotIn(self.env['SONAR_TOKEN'], arguments + result.stdout + result.stderr)
        self.assertNotIn('sonar.organization', arguments)

    def test_scanner_failure_is_not_swallowed(self):
        for status in ('1', '2', '124'):
            with self.subTest(status=status):
                self.env['SCANNER_EXIT'] = status
                self.assertEqual(self.run_scan().returncode, int(status))

    def test_cloud_organization_is_forwarded(self):
        self.env['SONAR_ORGANIZATION'] = 'demo-org'
        self.assertEqual(self.run_scan().returncode, 0)
        self.assertIn('-Dsonar.organization=demo-org\n', (self.root / 'arguments').read_text())

    def test_project_key_cannot_inject_shell_commands(self):
        self.env['SONAR_PROJECT_KEY'] = 'demo; touch unexpected'
        self.assertEqual(self.run_scan().returncode, 0)
        self.assertFalse((self.root / 'unexpected').exists())
        self.assertIn('-Dsonar.projectKey=demo; touch unexpected\n',
                      (self.root / 'arguments').read_text())


if __name__ == '__main__':
    unittest.main()
