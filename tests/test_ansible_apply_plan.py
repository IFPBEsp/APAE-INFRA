"""Testes da allowlist usada por .github/workflows/ansible-apply.yml."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ansible" / "scripts" / "apply-plan.sh"

PLAYBOOKS = [
    "check.yml",
    "prepare.yml",
    "hardening.yml",
    "k3s-preflight.yml",
    "k3s.yml",
    "k3s-verify.yml",
    "argocd.yml",
    "configure-runtime-tls.yml",
    "activate-compose.yml",
    "activate-cluster.yml",
]


class AnsibleApplyPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ansible_dir = Path(self.tmp.name)
        (self.ansible_dir / "playbooks").mkdir()
        for name in PLAYBOOKS:
            (self.ansible_dir / "playbooks" / name).write_text("---\n")
        inventory = self.ansible_dir / "inventories" / "production"
        inventory.mkdir(parents=True)
        (inventory / "hosts.yml").write_text("---\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_plan(self, **env):
        base = {
            "PATH": os.environ["PATH"],
            "ANSIBLE_DIR": str(self.ansible_dir),
            "GIT_REF": "refs/heads/main",
        }
        base.update(env)
        result = subprocess.run(
            ["bash", str(SCRIPT)], env=base, capture_output=True, text=True
        )
        outputs = dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )
        return result.returncode, outputs, result.stderr

    def dispatch(self, playbook, tags="todas", inventory="production", **env):
        return self.run_plan(
            EVENT_NAME="workflow_dispatch",
            INPUT_PLAYBOOK=playbook,
            INPUT_TAGS=tags,
            INPUT_INVENTORY=inventory,
            **env,
        )

    def test_push_on_main_runs_baseline(self):
        code, out, _ = self.run_plan(EVENT_NAME="push")
        self.assertEqual(code, 0)
        self.assertEqual(out["profile"], "baseline")
        self.assertEqual(out["playbooks"], "prepare.yml hardening.yml")
        self.assertEqual(out["health_checks"], "check.yml")
        self.assertEqual(out["environment"], "production")
        self.assertEqual(out["tags"], "")
        self.assertEqual(out["needs_vault"], "false")

    def test_push_ignores_dispatch_inputs(self):
        code, out, _ = self.run_plan(EVENT_NAME="push", INPUT_PLAYBOOK="argocd")
        self.assertEqual(code, 0)
        self.assertEqual(out["profile"], "baseline")

    def test_rejects_refs_other_than_main(self):
        for ref in ("refs/heads/dev", "refs/tags/v1", "refs/pull/1/merge", ""):
            for event in ("push", "workflow_dispatch"):
                with self.subTest(ref=ref, event=event):
                    code, _, err = self.run_plan(
                        EVENT_NAME=event,
                        GIT_REF=ref,
                        INPUT_PLAYBOOK="check",
                        INPUT_INVENTORY="production",
                    )
                    self.assertNotEqual(code, 0)
                    self.assertIn("refs/heads/main", err)

    def test_rejects_unexpected_events(self):
        for event in ("pull_request", "pull_request_target", "schedule", ""):
            with self.subTest(event=event):
                code, _, _ = self.run_plan(EVENT_NAME=event)
                self.assertNotEqual(code, 0)

    def test_dispatch_profiles(self):
        cases = {
            "check": ("check.yml", "check.yml"),
            "k3s": ("k3s-preflight.yml k3s.yml", "check.yml k3s-verify.yml"),
            "argocd": ("argocd.yml", "check.yml k3s-verify.yml"),
        }
        for profile, (playbooks, checks) in cases.items():
            with self.subTest(profile=profile):
                code, out, _ = self.dispatch(profile)
                self.assertEqual(code, 0)
                self.assertEqual(out["playbooks"], playbooks)
                self.assertEqual(out["health_checks"], checks)

    def test_vault_only_for_encrypted_playbooks(self):
        self.assertEqual(self.dispatch("argocd")[1]["needs_vault"], "true")
        self.assertEqual(self.dispatch("k3s")[1]["needs_vault"], "false")

    def test_rejects_arbitrary_playbooks_and_paths(self):
        for value in (
            "activate-compose",
            "activate-cluster",
            "check.yml",
            "../playbooks/check",
            "/etc/passwd",
            "check; id",
            "$(id)",
            "",
        ):
            with self.subTest(value=value):
                code, out, _ = self.dispatch(value)
                self.assertNotEqual(code, 0)
                self.assertNotIn("playbooks", out)

    def test_rejects_unlisted_tags(self):
        for tags in ("ssh", "all", "never", "x,--extra-vars=@/tmp/a", ""):
            with self.subTest(tags=tags):
                code, _, _ = self.dispatch("hardening", tags=tags)
                self.assertNotEqual(code, 0)

    def test_rejects_unlisted_inventories(self):
        for inventory in ("staging", "../production", "production/hosts.yml", ""):
            with self.subTest(inventory=inventory):
                code, _, _ = self.dispatch("check", inventory=inventory)
                self.assertNotEqual(code, 0)

    def test_fails_when_playbook_file_is_missing(self):
        (self.ansible_dir / "playbooks" / "k3s.yml").unlink()
        code, _, err = self.dispatch("k3s")
        self.assertNotEqual(code, 0)
        self.assertIn("playbooks/k3s.yml", err)

    def test_writes_github_output(self):
        output = self.ansible_dir / "github_output"
        code, _, _ = self.run_plan(EVENT_NAME="push", GITHUB_OUTPUT=str(output))
        self.assertEqual(code, 0)
        self.assertIn("playbooks=prepare.yml hardening.yml\n", output.read_text())


if __name__ == "__main__":
    unittest.main()
