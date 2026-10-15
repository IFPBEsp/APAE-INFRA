"""Exercise the workflow's own scripts against disposable Kustomize fixtures."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load(
    (ROOT / ".github/workflows/update-image-overlay-reusable.yml").read_text()
)
STEPS = WORKFLOW["jobs"]["update-image"]["steps"]
VALIDATE = next(step["run"] for step in STEPS if step["name"] == "Validate workflow inputs")
UPDATE = next(step["run"] for step in STEPS if step.get("id") == "image-update")
# Execute the Python embedded in the actual workflow, without its virtualenv wrapper.
EDITOR = UPDATE.split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]
IMAGE = "ghcr.io/ifpbesp/apae-geral-backend"
OTHER = "ghcr.io/ifpbesp/apae-geral-frontend:dev"
DIGEST = "sha256:" + "a" * 64
ENV = {
    "APPLICATION": "apae-geral",
    "ENVIRONMENT": "dev",
    "IMAGE": IMAGE,
    "IMAGE_DIGEST": DIGEST,
    "IMAGE_TAG": "sha-abcdef0",
    "SOURCE_COMMIT": "abcdef0" + "0" * 33,
    "SOURCE_REPOSITORY": "IFPBEsp/APAE",
    "CALLER_REPOSITORY": "IFPBEsp/APAE-INFRA",
}


class InputsTest(unittest.TestCase):
    def validate(self, **overrides):
        return subprocess.run(
            ["bash", "-c", VALIDATE], env={**os.environ, **ENV, **overrides},
            capture_output=True, text=True,
        )

    def test_valid_dispatch_and_direct_call(self):
        self.assertEqual(self.validate().returncode, 0)
        self.assertEqual(self.validate(CALLER_REPOSITORY="IFPBEsp/APAE").returncode, 0)

    def test_rejects_invalid_or_cross_application_payloads(self):
        for overrides in (
            {"IMAGE": "ghcr.io/ifpbesp/apae-atendimento-backend"},
            {"IMAGE": "ghcr.io/other/image"},
            {"APPLICATION": "../../etc"},
            {"ENVIRONMENT": "prod"},
            {"IMAGE_DIGEST": "sha256:bad"},
            {"IMAGE_TAG": "sha-1234567"},
            {"SOURCE_COMMIT": "invalid"},
            {"SOURCE_REPOSITORY": "IFPBEsp/APAE-atendimento"},
            {"CALLER_REPOSITORY": "other/repository"},
        ):
            with self.subTest(overrides=overrides):
                self.assertNotEqual(self.validate(**overrides).returncode, 0)

    def test_accepts_long_matching_sha_tag(self):
        self.assertEqual(self.validate(IMAGE_TAG="sha-" + ENV["SOURCE_COMMIT"]).returncode, 0)

    def test_all_known_services_are_allowed(self):
        for repository, application, images in (
            ("IFPBEsp/APAE", "apae-geral", ("apae-geral-backend", "apae-geral-frontend")),
            ("IFPBEsp/APAE-atendimento", "apae-atendimento",
             ("apae-atendimento-backend", "apae-atendimento-frontend")),
            ("IFPBEsp/apae-site-comemorativo", "site-comemorativo", ("apae-site-comemorativo",)),
        ):
            for image in images:
                with self.subTest(image=image):
                    result = self.validate(SOURCE_REPOSITORY=repository, APPLICATION=application,
                                           IMAGE="ghcr.io/ifpbesp/" + image)
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_overlay_reports_issue_92(self):
        script = next(step["run"] for step in STEPS if step.get("id") == "overlay")
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(["bash", "-c", script], cwd=directory,
                                    env={**os.environ, **ENV}, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue #92", result.stdout)


class OverlayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.kustomization = self.path / "kustomization.yaml"
        self.kustomization.write_text(
            "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
            "resources:\n- deployment.yaml\n"
        )
        (self.path / "deployment.yaml").write_text(yaml.safe_dump({
            "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "test"},
            "spec": {"selector": {"matchLabels": {"app": "test"}}, "template": {
                "metadata": {"labels": {"app": "test"}}, "spec": {
                    "containers": [{"name": "api", "image": IMAGE + ":dev"},
                                   {"name": "frontend", "image": OTHER}],
                    "initContainers": [{"name": "migrate", "image": IMAGE + ":dev"}],
                },
            }},
        }))

    def edit(self, **overrides):
        return subprocess.run(
            [sys.executable, "-c", EDITOR], text=True, capture_output=True,
            env={**os.environ, **ENV, "OVERLAY": str(self.path),
                 "GITHUB_OUTPUT": str(self.path / "output"), **overrides},
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_adds_digest_preserves_other_images_and_is_idempotent(self):
        self.assert_success(self.edit())
        rendered = subprocess.check_output(["kubectl", "kustomize", str(self.path)], text=True)
        self.assertEqual(rendered.count(IMAGE + "@" + DIGEST), 2)
        self.assertIn(OTHER, rendered)
        first = self.kustomization.read_bytes()
        self.assert_success(self.edit())
        self.assertEqual(first, self.kustomization.read_bytes())
        self.assertIn("gitops/apae-geral/dev/apae-geral-backend", (self.path / "output").read_text())

    def test_replaces_tag_and_previous_digest(self):
        data = yaml.safe_load(self.kustomization.read_text())
        data["images"] = [{"name": IMAGE, "newTag": "sha-1234567", "digest": "sha256:" + "b" * 64}]
        self.kustomization.write_text(yaml.safe_dump(data))
        self.assert_success(self.edit())
        entry = yaml.safe_load(self.kustomization.read_text())["images"][0]
        self.assertEqual(entry["digest"], DIGEST)
        self.assertNotIn("newTag", entry)

    def test_supports_existing_image_alias(self):
        deployment = self.path / "deployment.yaml"
        deployment.write_text(deployment.read_text().replace(IMAGE + ":dev", "api:dev"))
        data = yaml.safe_load(self.kustomization.read_text())
        data["images"] = [{"name": "api", "newName": IMAGE, "newTag": "dev"}]
        self.kustomization.write_text(yaml.safe_dump(data))
        self.assert_success(self.edit())
        self.assertEqual(yaml.safe_load(self.kustomization.read_text())["images"][0]["name"], "api")

    def test_missing_image_fails_without_editing(self):
        before = self.kustomization.read_bytes()
        result = self.edit(IMAGE="ghcr.io/ifpbesp/not-in-overlay")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("não encontrada", result.stderr)
        self.assertEqual(before, self.kustomization.read_bytes())

    def test_broken_overlay_cannot_proceed(self):
        self.kustomization.write_text("resources:\n- missing.yaml\n")
        self.assertNotEqual(self.edit().returncode, 0)

    def test_ambiguous_rules_fail_without_editing(self):
        data = yaml.safe_load(self.kustomization.read_text())
        data["images"] = [{"name": IMAGE, "newTag": "dev"},
                          {"name": IMAGE, "newTag": "other"}]
        self.kustomization.write_text(yaml.safe_dump(data))
        before = self.kustomization.read_bytes()
        self.assertNotEqual(self.edit().returncode, 0)
        self.assertEqual(before, self.kustomization.read_bytes())


if __name__ == "__main__":
    unittest.main()
