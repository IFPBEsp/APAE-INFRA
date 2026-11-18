"""Validate self-repository references and the reusable commitlint trust boundary."""

import json
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return yaml.safe_load(path.read_text())


class WorkflowToolingTest(unittest.TestCase):
    def test_internal_references_resolve_and_match_declared_inputs(self):
        references = 0
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            for job in load(path)['jobs'].values():
                for caller in [job, *job.get('steps', [])]:
                    uses = caller.get('uses', '')
                    self.assertFalse(uses.startswith('./'), (path, uses))
                    if not uses.startswith('$/'):
                        continue
                    references += 1
                    target = ROOT / uses[2:]
                    self.assertTrue(target.resolve().is_relative_to(ROOT))
                    if target.is_dir():
                        target /= 'action.yml'
                        definition = load(target)
                        inputs = definition.get('inputs', {})
                    else:
                        definition = load(target)
                        triggers = definition.get('on', definition.get(True, {}))
                        self.assertIn('workflow_call', triggers, target)
                        inputs = (triggers['workflow_call'] or {}).get('inputs', {})
                    with self.subTest(caller=path, reference=uses):
                        provided = caller.get('with', {})
                        self.assertLessEqual(set(provided), set(inputs))
                        for name, options in inputs.items():
                            if options.get('required') and 'default' not in options:
                                self.assertIn(name, provided)
        self.assertGreater(references, 0)

    def test_commitlint_lock_fixes_direct_and_transitive_dependencies(self):
        folder = ROOT / '.github/tools/commitlint'
        manifest = json.loads((folder / 'package.json').read_text())
        lock = json.loads((folder / 'package-lock.json').read_text())
        self.assertEqual(manifest['dependencies'], lock['packages']['']['dependencies'])
        for name, version in manifest['dependencies'].items():
            self.assertEqual(version, lock['packages']['node_modules/' + name]['version'])
        for path, package in lock['packages'].items():
            if path:
                with self.subTest(package=path):
                    self.assertTrue(package['resolved'].startswith('https://registry.npmjs.org/'))
                    self.assertTrue(package['integrity'].startswith('sha512-'))

    def test_custom_config_still_uses_trusted_tooling_checkout(self):
        steps = load(ROOT / '.github/workflows/commitlint-reusable.yml')['jobs']['commitlint']['steps']
        checkout = next(step for step in steps if step.get('name') == 'Checkout shared commitlint tooling')
        self.assertNotIn('if', checkout)
        self.assertEqual(checkout['with']['repository'], '${{ job.workflow_repository }}')
        self.assertEqual(checkout['with']['ref'], '${{ job.workflow_sha }}')
        self.assertIn('.github/tools/commitlint', checkout['with']['sparse-checkout'])
        install = next(step for step in steps if step.get('id') == 'commitlint')['run']
        self.assertIn('npm ci', install)
        self.assertNotIn('npm install', install)
        self.assertIn('--ignore-scripts', install)
        for filename in ('package.json', 'package-lock.json'):
            self.assertIn(f'$GITHUB_WORKSPACE/.apae-infra/.github/tools/commitlint/{filename}', install)


if __name__ == '__main__':
    unittest.main()
