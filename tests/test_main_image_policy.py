"""Reject non-main sources and out-of-order builds using the real workflow scripts."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = yaml.safe_load((ROOT / '.github/workflows/docker-build-publish-image.yml').read_text())
RECEIVE = yaml.safe_load((ROOT / '.github/workflows/update-image-overlay-reusable.yml').read_text())
SHA = 'a' * 40


def step(workflow, job, name):
    return next(item for item in workflow['jobs'][job]['steps'] if item.get('name') == name)


class CurrentMainTest(unittest.TestCase):
    def checks(self):
        return [
            step(PUBLISH, 'build-and-scan', 'Verify source is current main'),
            step(PUBLISH, 'publish', 'Recheck main before promotion'),
            step(RECEIVE, 'update-image', 'Verify source is current main'),
            step(RECEIVE, 'update-image', 'Recheck main before opening pull request'),
        ]

    def execute(self, script, *, ref='refs/heads/main', head=SHA, exit_code=0):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'gh'
            fake.write_text(
                '#!/bin/sh\n'
                '[ "$*" = "api --method GET repos/IFPBEsp/APAE/git/ref/heads/main --jq .object.sha" ] || exit 99\n'
                'printf "%s\\n" "$TEST_HEAD"\n'
                'exit "$TEST_EXIT"\n'
            )
            fake.chmod(0o755)
            return subprocess.run(['bash', '-c', script], text=True, capture_output=True,
                                  env={**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                                       'SOURCE_REPOSITORY': 'IFPBEsp/APAE', 'SOURCE_REF': ref,
                                       'SOURCE_COMMIT': SHA, 'TEST_HEAD': head, 'TEST_EXIT': str(exit_code)})

    def test_accepts_latest_main_commit(self):
        for item in self.checks():
            with self.subTest(check=item['name']):
                result = self.execute(item['run'])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_dev_feature_and_tag_refs(self):
        for item in self.checks():
            for ref in ('refs/heads/dev', 'refs/heads/feature', 'refs/tags/v1.0.0'):
                with self.subTest(check=item['name'], ref=ref):
                    self.assertNotEqual(self.execute(item['run'], ref=ref).returncode, 0)

    def test_rejects_stale_builds_missing_main_and_bad_api_responses(self):
        for item in self.checks():
            for head, exit_code in [('b' * 40, 0), ('', 0), ('null', 0), (SHA + '\n' + SHA, 0), (SHA, 1)]:
                with self.subTest(check=item['name'], head=head, exit_code=exit_code):
                    self.assertNotEqual(self.execute(item['run'], head=head, exit_code=exit_code).returncode, 0)

    def test_manual_dispatch_from_dev_cannot_start_a_build(self):
        condition = PUBLISH['jobs']['build-and-scan']['if']
        self.assertIn("github.ref == 'refs/heads/main'", condition)
        self.assertIn("github.event_name == 'push'", condition)
        self.assertIn("github.event_name == 'workflow_dispatch'", condition)
        tags = step(PUBLISH, 'publish', 'Generate final tags')['with']['tags']
        self.assertNotIn('value=dev', tags)
        self.assertIn("value=latest,enable=${{ github.ref == 'refs/heads/main' }}", tags)

    def test_rechecks_after_verification_and_before_mutations(self):
        for workflow, job, before, check, after in [
            (PUBLISH, 'publish', 'Verify Cosign signature', 'Recheck main before promotion', 'Promote verified image to final tags'),
            (RECEIVE, 'update-image', 'Update and validate image reference', 'Recheck main before opening pull request', 'Create or update image pull request'),
            (RECEIVE, 'update-image', 'Validate workflow inputs', 'Verify source is current main', 'Verify published image in GHCR'),
        ]:
            names = [item.get('name') for item in workflow['jobs'][job]['steps']]
            self.assertLess(names.index(before), names.index(check))
            self.assertLess(names.index(check), names.index(after))


if __name__ == '__main__':
    unittest.main()
