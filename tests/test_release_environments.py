"""Run release scripts with the repository's actual manifests in disposable copies."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

import test_update_image_overlay as fixtures
from test_update_image_overlay import (
    ROOT, ENV, IMAGE, DIGEST, EDITOR, RELEASE_STEPS, STEPS,
    embedded_python,
)

PRODUCTS = {
    "apae-geral": ("IFPBEsp/APAE", "apae-geral"),
    "apae-atendimento": ("IFPBEsp/APAE-atendimento", "apae-atendimento"),
    "apae-gestao-escolar": ("IFPBEsp/APAE-gestao-escolar", "gestao-escolar"),
    "site-comemorativo": ("IFPBEsp/apae-site-comemorativo", "site-comemorativo"),
}


class WorkflowRoutingTest(unittest.TestCase):
    def test_dispatch_and_release_jobs_execute_on_default_branch_but_write_to_main(self):
        workflows = ROOT / ".github/workflows"
        paths = ["update-image-overlay-reusable.yml", "approve-release.yml",
                 "promote-release.yml", "rollback-release.yml"]
        for path in paths:
            jobs = yaml.safe_load((workflows / path).read_text())["jobs"]
            for name, job in jobs.items():
                with self.subTest(workflow=path, job=name):
                    conditions = job["if"].split(" && ")
                    self.assertEqual(conditions[:2], [
                        "github.repository == 'IFPBEsp/APAE-INFRA'",
                        "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)",
                    ])
                    selectors = {"update-image": ["inputs.release-json == ''"],
                                 "update-release": ["inputs.release-json != ''"]}
                    self.assertEqual(conditions[2:], selectors.get(name, []))
                    bases = [s["with"]["base"] for s in job["steps"] if "base" in s.get("with", {})]
                    self.assertEqual(bases, ["main"])


class RealEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = self.root / "approved-main"
        self.main.mkdir()
        shutil.copytree(ROOT / "kubernetes", self.main / "kubernetes")
        self.production = self.root / "production"
        shutil.copytree(self.main, self.production)
        self.output = self.root / "outputs"
        self.workflows = {name: yaml.safe_load((ROOT / f".github/workflows/{name}-release.yml").read_text())
                          for name in ("approve", "promote", "rollback")}

    def execute(self, code, cwd, application, **extra):
        return subprocess.run([sys.executable, "-c", code], cwd=cwd, capture_output=True, text=True,
                              env={**os.environ, **ENV, "RUNNER_TEMP": str(self.root),
                                   "GITHUB_OUTPUT": str(self.output), "APPLICATION": application,
                                   "CANDIDATE_COMMIT": ENV["SOURCE_COMMIT"],
                                   "EVIDENCE_URL": "https://github.com/IFPBEsp/APAE-INFRA/issues/106",
                                   "APPROVAL_REASON": "Validacao funcional e dos digests em homologacao",
                                   "PROMOTION_REASON": "Promocao dos digests aprovados na homologacao",
                                   "ROLLBACK_REASON": "Restauracao de versao aprovada apos regressao",
                                   "APPROVER": "reviewer",
                                   "APPROVAL_RUN": "https://github.com/IFPBEsp/APAE-INFRA/actions/runs/42",
                                   "PATH": str(self.root) + ":" + os.environ["PATH"], **extra})

    def code(self, workflow, step_name):
        job = next(iter(self.workflows[workflow]["jobs"].values()))
        return embedded_python(next(s for s in job["steps"] if s.get("name") == step_name))

    def render(self, directory):
        result = subprocess.check_output(["kustomize", "build", str(directory)], text=True)
        return list(yaml.safe_load_all(result))

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_receive_approve_promote_and_rollback_with_real_overlays_for_all_products(self):
        for application, (repository, directory) in PRODUCTS.items():
            with self.subTest(application=application):
                hml = self.main / "kubernetes" / directory / "overlays/dev"
                prod = self.production / "kubernetes" / directory / "overlays/prod"
                if application == "site-comemorativo":
                    self.assert_success(self.execute(EDITOR, self.main, application,
                        OVERLAY=str(hml), VERIFICATION_RUN="https://github.com/IFPBEsp/APAE-INFRA/actions/runs/99"))
                    targets = {IMAGE: DIGEST}
                else:
                    release = fixtures.ReleaseDispatchTest().valid_release()
                    run = f"https://github.com/{repository}/actions/runs/123456"
                    release.update(application=application, source_repository=repository, workflow_run=run)
                    for component, item in release["images"].items():
                        item.update(image=f"ghcr.io/ifpbesp/{application}-{component}", workflow_run=run)
                    (self.root / "verified-release-input.json").write_text(json.dumps(release))
                    update = next(s for s in RELEASE_STEPS if s.get("id") == "release-update")
                    self.assert_success(self.execute(embedded_python(update), self.main, application))
                    targets = {item["image"]: item["digest"] for item in release["images"].values()}

                self.assert_success(self.execute(self.code("approve", "Validate candidate, deployed overlay intent and evidence"),
                                                 self.main, application))
                self.assert_success(self.execute(self.code("promote", "Validate merged approval and candidate integrity"),
                                                 self.root, application))
                initial = self.render(prod)
                self.assert_success(self.execute(self.code("promote", "Apply only approved digests and validate Kustomize"),
                                                 self.production, application))
                promoted = self.render(prod)
                for doc in promoted:
                    self.assertEqual(doc["metadata"]["namespace"], "apae-prod")
                    if doc["kind"] == "Deployment":
                        self.assertEqual(doc["spec"]["replicas"], 0)
                refs = [c["image"] for doc in promoted if doc["kind"] == "Deployment"
                        for c in doc["spec"]["template"]["spec"]["containers"]]
                for image, digest in targets.items():
                    self.assertIn(image + "@" + digest, refs)
                # The promotion must change only the product image references.
                for doc in initial:
                    if doc["kind"] == "Deployment":
                        for container in doc["spec"]["template"]["spec"]["containers"]:
                            image = container["image"].split(":", 1)[0]
                            if image in targets:
                                container["image"] = image + "@" + targets[image]
                self.assertEqual(initial, promoted)

                # Model a later production version and a merged earlier version.
                self.assert_success(self.execute(self.code("rollback", "Validate approved release record"), self.root, application))
                path = prod / "kustomization.yaml"
                historical = self.root / "historical.yaml"
                historical.write_bytes(path.read_bytes())
                data = yaml.safe_load(path.read_text())
                for item in data["images"]:
                    item["digest"] = "sha256:" + "f" * 64
                path.write_text(yaml.safe_dump(data))
                fake_git = self.root / "git"
                fake_git.write_text("#!/usr/bin/env python3\nimport os, pathlib, sys\n"
                    "if sys.argv[1] == 'log': print('d' * 40)\n"
                    "elif sys.argv[1] == 'show': print((pathlib.Path(os.environ['RUNNER_TEMP']) / 'historical.yaml').read_text())\n"
                    "else: raise SystemExit(99)\n")
                fake_git.chmod(0o755)
                self.assert_success(self.execute(self.code("rollback", "Confirm historical production deployment and prepare rollback"),
                                                 self.production, application))
                self.assertEqual(self.render(prod), promoted)
                self.assertIn(f"overlay_path=kubernetes/{directory}/overlays/prod/kustomization.yaml", self.output.read_text())

    def test_applications_follow_main_with_manual_sync_and_correct_namespaces(self):
        root = yaml.safe_load((ROOT / "argocd/app-of-apps.yaml").read_text())
        self.assertNotIn("automated", root["spec"]["syncPolicy"])
        self.assertEqual(root["spec"]["source"]["targetRevision"], "main")
        seen = set()
        for environment in ("dev", "prod"):
            for _, directory in PRODUCTS.values():
                path = ROOT / f"argocd/apps/{environment}/{directory}-{environment}.yaml"
                app = yaml.safe_load(path.read_text())
                self.assertNotIn("automated", app["spec"]["syncPolicy"])
                source = app["spec"]["source"]
                self.assertEqual(source["targetRevision"], "main")
                self.assertEqual(source["path"], f"kubernetes/{directory}/overlays/{environment}")
                namespace = f"apae-{environment}"
                self.assertEqual(app["spec"]["destination"]["namespace"], namespace)
                for doc in self.render(ROOT / source["path"]):
                    key = (doc["apiVersion"], doc["kind"], doc["metadata"]["namespace"], doc["metadata"]["name"])
                    self.assertNotIn(key, seen)
                    seen.add(key)


class SignatureIdentityTest(unittest.TestCase):
    def test_producer_and_receivers_accept_only_the_authorized_reusable_identity(self):
        publisher = yaml.safe_load((ROOT / ".github/workflows/docker-build-publish-image.yml").read_text())
        steps = [next(s for s in publisher["jobs"]["publish"]["steps"] if s.get("name") == "Verify Cosign signature"),
                 next(s for s in STEPS if s.get("name") == "Verify published Cosign signature"),
                 next(s for s in RELEASE_STEPS if s.get("name") == "Verify both Cosign signatures")]
        prefix = "https://github.com/IFPBEsp/APAE-INFRA/.github/workflows/docker-build-publish-image.yml@"
        for step in steps:
            pattern = re.search(r"--certificate-identity-regexp='([^']+)'", step["run"]).group(1)
            for identity, accepted in [(prefix + "refs/heads/main", True), (prefix + "a" * 40, True),
                                       (prefix + "refs/heads/dev", False), (prefix + "refs/heads/feature", False),
                                       ("https://github.com/IFPBEsp/APAE/.github/workflows/build.yml@refs/heads/main", False),
                                       (prefix.replace("IFPBEsp", "other") + "refs/heads/main", False)]:
                self.assertEqual(re.fullmatch(pattern, identity) is not None, accepted)
            for flag in ("--certificate-oidc-issuer", "--certificate-github-workflow-repository",
                         "--certificate-github-workflow-ref", "--certificate-github-workflow-sha"):
                self.assertIn(flag, step["run"])

    def test_site_records_only_an_authenticated_publication_run(self):
        verifier = next(s for s in STEPS if s.get("name") == "Verify image build provenance")
        run = ENV["SOURCE_WORKFLOW_RUN"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "gh"
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_ATTESTATION"\nexit "$VERIFY_EXIT"\n')
            fake.chmod(0o755)
            for invocations, exit_code, accepted in [
                ([run + "/attempts/1"], 0, True),
                ([run + "/attempts/1"], 1, False),
                ([], 0, False), ([None], 0, False),
                ([run], 0, False),
                ([run.replace("apae-site-comemorativo", "APAE") + "/attempts/1"], 0, False),
                ([run + "/attempts/1", run + "/attempts/2"], 0, False),
                ([run + "/other/actions/runs/999/attempts/1"], 0, False),
            ]:
                with self.subTest(invocations=invocations, exit_code=exit_code):
                    output = root / "outputs"
                    output.unlink(missing_ok=True)
                    attestations = [{"verificationResult": {"statement": {"predicate": {
                        "runDetails": {"metadata": {"invocationId": invocation}}
                    }}}} for invocation in invocations]
                    result = subprocess.run(["bash", "-c", verifier["run"]], capture_output=True, text=True,
                        env={**os.environ, **ENV, "RUNNER_TEMP": directory, "GITHUB_OUTPUT": str(output),
                             "PATH": directory + ":" + os.environ["PATH"], "VERIFY_EXIT": str(exit_code),
                             "TEST_ATTESTATION": json.dumps(attestations)})
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
                    if accepted:
                        self.assertEqual(output.read_text(), f"workflow_run={run}\n")
                    else:
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
