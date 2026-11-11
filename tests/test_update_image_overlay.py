"""Exercise the workflow's own scripts against disposable Kustomize fixtures."""

import base64
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.parse

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load(
    (ROOT / ".github/workflows/update-image-overlay-reusable.yml").read_text()
)
STEPS = WORKFLOW["jobs"]["update-image"]["steps"]
VALIDATE = next(step["run"] for step in STEPS if step["name"] == "Validate workflow inputs")
AUTOMATION = next(step for step in STEPS if step.get("id") == "automation")
MANIFESTS = next(step for step in STEPS if step.get("id") == "manifests")
OVERLAY_STEP = next(step for step in STEPS if step.get("id") == "overlay")
UPDATE_STEP = next(step for step in STEPS if step.get("id") == "image-update")
PULL_REQUEST = next(step for step in STEPS if step.get("id") == "pull-request")
UPDATE = UPDATE_STEP["run"]
# Execute the Python embedded in the actual workflow, without its virtualenv wrapper.
EDITOR = UPDATE.split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]
REGISTRY_SCRIPT = next(step["run"] for step in STEPS if step.get("id") == "registry")
REGISTRY_CODE = (ROOT / "scripts/ci/verify_ghcr_image.py").read_text(encoding="utf-8")
REGISTRY = {"__name__": "registry_test"}
exec(compile(REGISTRY_CODE, "scripts/ci/verify_ghcr_image.py", "exec"), REGISTRY)
DISPATCH = yaml.safe_load((ROOT / ".github/workflows/update-image-overlay-dispatch.yml").read_text())
PAYLOAD_SCRIPT = DISPATCH["jobs"]["validate-payload"]["steps"][0]["run"]
RELEASE_PAYLOAD_SCRIPT = DISPATCH["jobs"]["validate-release"]["steps"][0]["run"]
RELEASE_STEPS = WORKFLOW["jobs"]["update-release"]["steps"]
SETUP = yaml.safe_load((ROOT / ".github/actions/setup-kustomize/action.yml").read_text())
IMAGE = "ghcr.io/ifpbesp/apae-site-comemorativo"
OTHER = "ghcr.io/ifpbesp/apae-geral-frontend:dev"
DIGEST = "sha256:" + "a" * 64
ENV = {
    "APPLICATION": "site-comemorativo",
    "ENVIRONMENT": "dev",
    "IMAGE": IMAGE,
    "IMAGE_DIGEST": DIGEST,
    "IMAGE_TAG": "sha-abcdef0",
    "SOURCE_COMMIT": "abcdef0" + "0" * 33,
    "SOURCE_WORKFLOW_RUN": "https://github.com/IFPBEsp/apae-site-comemorativo/actions/runs/123456",
    "SOURCE_REPOSITORY": "IFPBEsp/apae-site-comemorativo",
    "CALLER_REPOSITORY": "IFPBEsp/APAE-INFRA",
}


def setUpModule():
    expected = "v" + SETUP["runs"]["steps"][0]["env"]["KUSTOMIZE_VERSION"]
    actual = subprocess.check_output(["kustomize", "version"], text=True).strip()
    if actual != expected:
        raise RuntimeError(f"Os testes exigem Kustomize {expected}; encontrado {actual}.")


class InputsTest(unittest.TestCase):
    def validate(self, **overrides):
        return subprocess.run(
            ["bash", "-c", VALIDATE], env={**os.environ, **ENV, **overrides},
            capture_output=True, text=True,
        )

    def test_valid_infra_call(self):
        self.assertEqual(self.validate().returncode, 0)

    def test_rejects_invalid_or_cross_application_payloads(self):
        for overrides in (
            {"IMAGE": "ghcr.io/ifpbesp/apae-atendimento-backend"},
            {"IMAGE": "ghcr.io/other/image"},
            {"APPLICATION": "../../etc"},
            {"ENVIRONMENT": "prod"},
            {"ENVIRONMENT": "hml"},
            {"ENVIRONMENT": ""},
            {"IMAGE_DIGEST": "sha256:bad"},
            {"IMAGE_TAG": "sha-1234567"},
            {"IMAGE_TAG": "latest"},
            {"SOURCE_COMMIT": "invalid"},
            {"SOURCE_REPOSITORY": "IFPBEsp/APAE-atendimento"},
            {"CALLER_REPOSITORY": "other/repository"},
            {"CALLER_REPOSITORY": "IFPBEsp/APAE"},
            {"IMAGE": "ghcr.io/ifpbesp/apae-geral-backend/../../other"},
            {"SOURCE_COMMIT": "$(touch /tmp/should-not-run)"},
        ):
            with self.subTest(overrides=overrides):
                self.assertNotEqual(self.validate(**overrides).returncode, 0)

    def test_accepts_long_matching_sha_tag(self):
        self.assertEqual(self.validate(IMAGE_TAG="sha-" + ENV["SOURCE_COMMIT"]).returncode, 0)

    def test_only_site_uses_single_image_and_joint_products_are_rejected(self):
        for repository, application, images in (
            ("IFPBEsp/APAE", "apae-geral", ("apae-geral-backend", "apae-geral-frontend")),
            ("IFPBEsp/APAE-atendimento", "apae-atendimento",
             ("apae-atendimento-backend", "apae-atendimento-frontend")),
            ("IFPBEsp/APAE-gestao-escolar", "apae-gestao-escolar",
             ("apae-gestao-escolar-backend", "apae-gestao-escolar-frontend")),
            ("IFPBEsp/apae-site-comemorativo", "site-comemorativo", ("apae-site-comemorativo",)),
        ):
            for image in images:
                with self.subTest(image=image):
                    result = self.validate(SOURCE_REPOSITORY=repository, APPLICATION=application,
                                           IMAGE="ghcr.io/ifpbesp/" + image)
                    if application == "site-comemorativo":
                        self.assertEqual(result.returncode, 0, result.stdout)
                    else:
                        self.assertNotEqual(result.returncode, 0)

    def test_missing_overlay_reports_issue_92(self):
        script = next(step["run"] for step in STEPS if step.get("id") == "overlay")
        with tempfile.TemporaryDirectory() as directory:
            manifests = Path(directory) / OVERLAY_STEP["working-directory"]
            manifests.mkdir()
            result = subprocess.run(["bash", "-c", script], cwd=manifests,
                                    env={**os.environ, **ENV}, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue #92", result.stdout)


class DispatchTest(unittest.TestCase):
    def test_app_credentials_are_scoped_to_fixed_environment(self):
        self.assertEqual(WORKFLOW["jobs"]["update-image"]["environment"], "gitops-image-updater")
        declared = WORKFLOW["on"]["workflow_call"]["secrets"] if "on" in WORKFLOW else WORKFLOW[True]["workflow_call"]["secrets"]
        forwarded = DISPATCH["jobs"]["update-overlay"]["secrets"]
        for name in ("IMAGE_UPDATER_APP_ID", "IMAGE_UPDATER_APP_PRIVATE_KEY"):
            with self.subTest(secret=name):
                self.assertFalse(declared[name]["required"])
                self.assertNotIn(name, forwarded)

    def payload(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            result = subprocess.run(
                ["bash", "-c", PAYLOAD_SCRIPT], text=True, capture_output=True,
                env={**os.environ, "PAYLOAD": json.dumps(payload), "GITHUB_OUTPUT": str(output)},
            )
            return result, output.read_text() if output.exists() else ""

    def valid_payload(self):
        return {"application": "site-comemorativo",
                "image": "ghcr.io/ifpbesp/apae-site-comemorativo",
                "image_tag": ENV["IMAGE_TAG"], "image_digest": DIGEST,
                "source_repository": "IFPBEsp/apae-site-comemorativo",
                "source_commit": ENV["SOURCE_COMMIT"]}

    def test_default_environment_only_when_omitted(self):
        result, output = self.payload(self.valid_payload())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("environment=dev\n", output)
        for value in (None, False, 0, "", [], {}, "hml", "prod", "DEV"):
            with self.subTest(value=value):
                result, output = self.payload({**self.valid_payload(), "environment": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")

    def test_rejects_partial_apae_release_via_single_image_dispatch(self):
        for component in ("backend", "frontend"):
            with self.subTest(component=component):
                payload = {
                    **self.valid_payload(),
                    "application": "apae-geral",
                    "source_repository": "IFPBEsp/APAE",
                    "image": f"ghcr.io/ifpbesp/apae-geral-{component}",
                }
                result, output = self.payload(payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")
                self.assertIn("gitops-release-published", result.stderr)

    def test_missing_unknown_non_string_and_output_injection_rejected(self):
        for payload in (
            {}, [], {**self.valid_payload(), "path": "../../etc"},
            {**self.valid_payload(), "image": IMAGE + "\napplication=other"},
            {**self.valid_payload(), "source_commit": 123},
        ):
            with self.subTest(payload=payload):
                result, output = self.payload(payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")

    def test_registry_gate_precedes_app_token_and_writes(self):
        ids = [step.get("id") for step in STEPS]
        self.assertLess(ids.index("registry"), ids.index("app-token"))
        self.assertLess(ids.index("registry"), ids.index("image-update"))
        self.assertLess(ids.index("registry"), ids.index("pull-request"))

    def test_app_token_is_limited_to_infra(self):
        token = next(step for step in STEPS if step.get("id") == "app-token")
        self.assertEqual(token["with"]["owner"], "IFPBEsp")
        self.assertEqual(token["with"]["repositories"], "APAE-INFRA")
        permissions = {key: value for key, value in token["with"].items() if key.startswith("permission-")}
        self.assertEqual(permissions, {"permission-contents": "write", "permission-pull-requests": "write"})


class ReleaseDispatchTest(unittest.TestCase):
    def valid_release(self):
        return {
            "application": "apae-geral",
            "source_repository": "IFPBEsp/APAE",
            "source_commit": ENV["SOURCE_COMMIT"],
            "workflow_run": "https://github.com/IFPBEsp/APAE/actions/runs/123456",
            "images": {
                part: {
                    "image": f"ghcr.io/ifpbesp/apae-geral-{part}",
                    "tag": ENV["IMAGE_TAG"],
                    "digest": "sha256:" + char * 64,
                    "workflow_run": "https://github.com/IFPBEsp/APAE/actions/runs/123456",
                }
                for part, char in (("backend", "a"), ("frontend", "b"))
            },
        }

    def validate(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "outputs"
            result = subprocess.run(
                ["bash", "-c", RELEASE_PAYLOAD_SCRIPT],
                env={**os.environ, "PAYLOAD": json.dumps(payload), "GITHUB_OUTPUT": str(output_path)},
                capture_output=True, text=True,
            )
            outputs = output_path.read_text() if output_path.exists() else ""
        return result, outputs

    def test_complete_release_is_accepted(self):
        payload = self.valid_release()
        result, outputs = self.validate(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("application=apae-geral\n", outputs)
        self.assertIn("environment=dev\n", outputs)
        self.assertIn("release_json=", outputs)
        encoded = next(line.split("=", 1)[1] for line in outputs.splitlines()
                       if line.startswith("release_json="))
        self.assertEqual(json.loads(encoded), payload)

    def test_rejects_partial_or_inconsistent_releases(self):
        base = self.valid_release()
        variants = []
        variants.append({**base, "images": {"backend": base["images"]["backend"]}})
        variants.append({**base, "images": {"frontend": base["images"]["frontend"]}})
        variants.append({**base, "application": "apae-atendimento"})
        variants.append({**base, "source_repository": "other/repo"})
        variants.append({**base, "source_commit": "not-a-commit"})
        variants.append({**base, "workflow_run": "https://example.com/123"})
        variants.append({**base, "environment": "prod"})
        variants.append({**base, "images": {**base["images"], "backend": {
            **base["images"]["backend"], "digest": "sha256:wrong"}}})
        variants.append({**base, "images": {**base["images"], "frontend": {
            **base["images"]["frontend"], "tag": "sha-0000000"}}})
        variants.append({**base, "images": {**base["images"], "frontend": {
            **base["images"]["frontend"], "workflow_run": "https://github.com/IFPBEsp/APAE/actions/runs/999"}}})
        variants.append({**base, "images": {**base["images"], "backend": {
            **base["images"]["backend"], "image": "ghcr.io/other/backend"}}})
        variants.extend(({}, [], None))
        for payload in variants:
            with self.subTest(payload=payload):
                result, outputs = self.validate(payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(outputs, "")

    def test_dispatch_routes_events_to_the_correct_workflow(self):
        jobs = DISPATCH["jobs"]
        self.assertEqual(jobs["validate-payload"]["if"],
                         "github.event.action == 'gitops-image-published'")
        self.assertEqual(jobs["validate-release"]["if"],
                         "github.event.action == 'gitops-release-published'")
        self.assertEqual(jobs["update-overlay"]["needs"], "validate-payload")
        self.assertEqual(jobs["update-release-overlay"]["needs"], "validate-release")
        release_inputs = jobs["update-release-overlay"]["with"]
        self.assertIn("release-json", release_inputs)
        self.assertNotIn("image", release_inputs)
        self.assertNotIn("image-tag", release_inputs)
        self.assertNotIn("image-digest", release_inputs)
        self.assertNotIn("IMAGE_UPDATER_APP_PRIVATE_KEY", jobs["update-release-overlay"]["secrets"])

    def test_two_image_verification_precedes_app_token_and_writes(self):
        names = [step["name"] for step in RELEASE_STEPS]
        registry = names.index("Verify both GHCR tags and digests")
        provenance = names.index("Verify both build attestations")
        app = names.index("Generate image updater GitHub App token")
        update = names.index("Update both digests and record candidate atomically")
        pr = names.index("Create or update complete release PR")
        self.assertLess(registry, provenance)
        self.assertLess(provenance, app)
        self.assertLess(app, update)
        self.assertLess(update, pr)
        self.assertIn("for component in backend frontend", RELEASE_STEPS[registry]["run"])
        self.assertIn("verify_ghcr_image.py", RELEASE_STEPS[registry]["run"])
        provenance_script = RELEASE_STEPS[provenance]["run"]
        self.assertIn("for component in backend frontend", provenance_script)
        for flag in ("--bundle-from-oci", "--repo", "--signer-workflow",
                     "--source-ref", "--source-digest"):
            self.assertIn(flag, provenance_script)

    def test_release_pr_updates_main_and_tracks_candidate(self):
        release = WORKFLOW["jobs"]["update-release"]
        self.assertEqual(release["environment"], "gitops-image-updater")
        checkout = next(step for step in RELEASE_STEPS
                        if step["name"] == "Checkout homologation manifests")
        self.assertEqual(checkout["with"]["ref"], "main")
        pr = next(step for step in RELEASE_STEPS if step["name"] == "Create or update complete release PR")
        self.assertEqual(pr["with"]["base"], "main")
        self.assertEqual(pr["with"]["add-paths"].splitlines(), [
            "${{ steps.release-update.outputs.overlay }}", "${{ steps.release-update.outputs.candidate }}"])
        self.assertNotIn("auto-merge", pr["with"])
        token_step = next(step for step in RELEASE_STEPS if step["name"] == "Generate image updater GitHub App token")
        self.assertEqual(token_step["with"]["repositories"], "APAE-INFRA")
        self.assertEqual(
            {k: v for k, v in token_step["with"].items() if k.startswith("permission-")},
            {"permission-contents": "write", "permission-pull-requests": "write"},
        )



class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.opener = mock.Mock()
        patcher = mock.patch("urllib.request.build_opener", return_value=self.opener)
        patcher.start()
        self.addCleanup(patcher.stop)
        # This fixture is the object of the tag; no platform manifest is downloaded.
        self.body = json.dumps({"schemaVersion": 2, "mediaType": REGISTRY["MEDIA_TYPES"][0],
                                "manifests": [{"digest": DIGEST, "platform": {"os": "linux", "architecture": "amd64"}}]}).encode()
        self.digest = "sha256:" + hashlib.sha256(self.body).hexdigest()

    def response(self, body, headers=None):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = body
        response.headers = headers or {}
        return response

    def token(self, token="anonymous-token"):
        return self.response(json.dumps({"token": token}).encode())

    def manifest(self, body=None, media_type=None, digest=None):
        return self.response(self.body if body is None else body, {
            "Content-Type": media_type or REGISTRY["MEDIA_TYPES"][0],
            "Docker-Content-Digest": digest or self.digest,
        })

    def http_error(self, code):
        error = urllib.error.HTTPError("https://ghcr.io/", code, "sensitive-server-message", {}, None)
        self.addCleanup(error.close)
        return error

    def verify(self, **kwargs):
        return REGISTRY["verify_published_image"](IMAGE, ENV["IMAGE_TAG"], self.digest, **kwargs)

    def test_oci_and_docker_single_and_multiarch_objects(self):
        for media_type in REGISTRY["MEDIA_TYPES"]:
            with self.subTest(media_type=media_type):
                body = json.dumps({"schemaVersion": 2, "mediaType": media_type}).encode()
                digest = "sha256:" + hashlib.sha256(body).hexdigest()
                self.opener.open.side_effect = [self.token(), self.manifest(body, media_type, digest)]
                REGISTRY["verify_published_image"](IMAGE, ENV["IMAGE_TAG"], digest)
        request = self.opener.open.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/manifests/sha-abcdef0"))
        for media_type in REGISTRY["MEDIA_TYPES"]:
            self.assertIn(media_type, request.get_header("Accept"))

    def test_missing_tag_rejected(self):
        self.opener.open.side_effect = [self.token(), self.http_error(404)]
        with self.assertRaises(urllib.error.HTTPError):
            self.verify()

    def test_child_digest_is_not_the_multiarch_index_digest(self):
        self.opener.open.side_effect = [self.token(), self.manifest()]
        with self.assertRaises(ValueError):
            REGISTRY["verify_published_image"](IMAGE, ENV["IMAGE_TAG"], DIGEST)

    def test_header_digest_cannot_override_actual_body_digest(self):
        self.opener.open.side_effect = [self.token(), self.manifest(digest=DIGEST)]
        with self.assertRaises(ValueError):
            self.verify()

    def test_private_image_authenticated_after_anonymous_denial(self):
        for token_denied in (False, True):
            with self.subTest(token_denied=token_denied):
                initial = [self.http_error(401)] if token_denied else [self.token(), self.http_error(403)]
                self.opener.open.side_effect = initial + [self.token("private-token"), self.manifest()]
                self.verify(username="reader", password="read-only-password")
                calls = self.opener.open.call_args_list[-2:]
                token_request = calls[0].args[0]
                self.assertTrue(token_request.full_url.startswith("https://ghcr.io/token?"))
                self.assertEqual(token_request.get_header("Authorization"),
                                 "Basic " + base64.b64encode(b"reader:read-only-password").decode())
                scope = urllib.parse.parse_qs(urllib.parse.urlsplit(token_request.full_url).query)["scope"]
                self.assertEqual(scope, ["repository:" + IMAGE.removeprefix("ghcr.io/") + ":pull"])
                self.assertEqual(calls[1].args[0].get_header("Authorization"), "Bearer private-token")

    def test_authentication_failure_and_missing_credentials_rejected(self):
        for credentials in ({}, {"username": "reader", "password": "wrong-password"}):
            with self.subTest(credentials=credentials):
                self.opener.open.side_effect = self.http_error(401)
                with self.assertRaises(urllib.error.HTTPError):
                    self.verify(**credentials)

    def test_failures_are_closed_and_do_not_log_credentials(self):
        for error in (self.http_error(404), self.http_error(500),
                      urllib.error.URLError("read-only-password"), TimeoutError("private-token")):
            with self.subTest(error=type(error).__name__):
                self.opener.open.side_effect = error
                output = io.StringIO()
                with mock.patch.dict(os.environ, {**ENV, "IMAGE_DIGEST": self.digest,
                                                  "GHCR_READ_USERNAME": "reader",
                                                  "GHCR_READ_TOKEN": "read-only-password"}, clear=True):
                    with redirect_stdout(output):
                        self.assertEqual(REGISTRY["main"](), 1)
                self.assertNotIn("read-only-password", output.getvalue())
                self.assertNotIn("private-token", output.getvalue())
                self.assertNotIn("sensitive-server-message", output.getvalue())

    def test_invalid_registry_responses_fail(self):
        for responses in (
            [self.response(b"not-json")],
            [self.response(b'{"token": "invalid\\nheader"}')],
            [self.token(), self.response(b"{}", {"Content-Type": "text/html"})],
            [self.token(), self.manifest(body=b"not-json")],
            [self.token(), self.response(b"x" * (8 * 1024 * 1024 + 1))],
        ):
            with self.subTest():
                self.opener.open.side_effect = responses
                with self.assertRaises(ValueError):
                    self.verify()

    def test_redirects_do_not_forward_credentials(self):
        self.assertIsNone(REGISTRY["NoRedirect"]().redirect_request(None, None, 302, "", {}, "https://other.test/"))
        self.opener.open.side_effect = self.http_error(302)
        with self.assertRaises(urllib.error.HTTPError):
            self.verify(username="reader", password="read-only-password")

    def test_optional_pat_requires_username_and_token_together(self):
        with mock.patch.dict(os.environ, {**ENV, "GHCR_READ_TOKEN": "read-only-password"}, clear=True):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(REGISTRY["main"](), 1)
        self.opener.open.assert_not_called()

    def test_main_uses_infra_github_token_or_explicit_read_pat(self):
        for optional in ({}, {"GHCR_READ_USERNAME": "package-reader", "GHCR_READ_TOKEN": "read-pat"}):
            with self.subTest(optional=bool(optional)):
                self.opener.open.reset_mock()
                self.opener.open.side_effect = [self.http_error(401), self.token("private-token"), self.manifest()]
                with mock.patch.dict(os.environ, {**ENV, "IMAGE_DIGEST": self.digest,
                                                  "REGISTRY_USERNAME": "infra-actor",
                                                  "REGISTRY_TOKEN": "infra-github-token", **optional}, clear=True):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(REGISTRY["main"](), 0)
                request = self.opener.open.call_args_list[-2].args[0]
                expected = b"package-reader:read-pat" if optional else b"infra-actor:infra-github-token"
                self.assertEqual(request.get_header("Authorization"), "Basic " + base64.b64encode(expected).decode())

class ProvenanceTest(unittest.TestCase):
    def test_provenance_precedes_app_token(self):
        names = [step.get("name") for step in STEPS]

        registry = names.index("Verify published image in GHCR")
        provenance = names.index("Verify image build provenance")
        app_token = names.index("Generate GitHub App token")

        self.assertLess(registry, provenance)
        self.assertLess(provenance, app_token)

    def test_provenance_requires_authenticated_origin(self):
        step = next(
            step for step in STEPS
            if step.get("name") == "Verify image build provenance"
        )

        script = step["run"]

        for required in (
                "set -euo pipefail",
                "gh attestation verify",
                "--bundle-from-oci",
                "--repo",
                "--signer-workflow",
                "--source-ref",
                "--source-digest",
                "refs/heads/main",
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)

    def test_provenance_verification_fails_closed(self):
        step = next(
            step for step in STEPS
            if step.get("name") == "Verify image build provenance"
        )

        with tempfile.TemporaryDirectory() as directory:
            fake_gh = Path(directory) / "gh"

            for exit_code in (0, 1):
                with self.subTest(exit_code=exit_code):
                    attestation = [{"verificationResult": {"statement": {"predicate": {
                        "runDetails": {"metadata": {"invocationId": ENV["SOURCE_WORKFLOW_RUN"] + "/attempts/1"}}
                    }}}}]
                    fake_gh.write_text(
                        "#!/bin/sh\n" + "echo '" + json.dumps(attestation) + "'\n" + f"exit {exit_code}\n"
                    )
                    fake_gh.chmod(0o755)

                    result = subprocess.run(
                        ["bash", "-c", step["run"]],
                        env={
                            **os.environ,
                            **ENV,
                            "PATH": f"{directory}:{os.environ['PATH']}",
                            "RUNNER_TEMP": directory, "GITHUB_OUTPUT": str(Path(directory) / "outputs"),
                        },
                        capture_output=True,
                        text=True,
                    )

                    if exit_code == 0:
                        self.assertEqual(result.returncode, 0)
                        self.assertIn(
                            "Proveniência autenticada com sucesso",
                            result.stdout,
                        )
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn(
                            "Proveniência autenticada com sucesso",
                            result.stdout,
                        )

class PublisherSecurityTest(unittest.TestCase):
    def test_cosign_sign_and_verify_before_promotion(self):
        publisher = yaml.safe_load(
            (ROOT / ".github/workflows/docker-build-publish-image.yml").read_text()
        )

        publish_steps = publisher["jobs"]["publish"]["steps"]
        names = [step["name"] for step in publish_steps]

        sign = names.index("Sign candidate image with Cosign")
        verify = names.index("Verify Cosign signature")
        promote = names.index("Promote verified image to final tags")

        self.assertLess(sign, verify)
        self.assertLess(verify, promote)

        script = publish_steps[verify]["run"]

        for required in (
                "cosign verify",
                "--certificate-identity-regexp=",
                "--certificate-oidc-issuer=",
                "--certificate-github-workflow-repository=",
                "--certificate-github-workflow-ref=",
                "--certificate-github-workflow-sha=",
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)

class OverlayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.relative_overlay = Path("kubernetes/site-comemorativo/overlays/dev")
        self.manifests = self.workspace / MANIFESTS["with"]["path"]
        self.path = self.manifests / self.relative_overlay
        self.path.mkdir(parents=True)
        self.output = self.workspace / "step-output"
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
        # The automation checkout has the same logical overlay and the local
        # action, while the manifests checkout deliberately has no .github/actions directory.
        shutil.copytree(self.path, self.workspace / self.relative_overlay)
        self.local_action = self.workspace / ".github/actions/setup-kustomize/action.yml"
        self.local_action.parent.mkdir(parents=True)
        self.local_action.write_text((ROOT / ".github/actions/setup-kustomize/action.yml").read_text())

    def edit(self, **overrides):
        return subprocess.run(
            [sys.executable, "-c", EDITOR], text=True, capture_output=True,
            cwd=self.workspace / UPDATE_STEP["working-directory"],
            env={**os.environ, **ENV, "OVERLAY": str(self.relative_overlay),
                 "GITHUB_OUTPUT": str(self.output),
                 "VERIFICATION_RUN": "https://github.com/IFPBEsp/APAE-INFRA/actions/runs/42", **overrides},
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_adds_digest_preserves_other_images_and_is_idempotent(self):
        self.assert_success(self.edit())
        rendered = subprocess.check_output(["kustomize", "build", str(self.path)], text=True)
        self.assertEqual(rendered.count(IMAGE + "@" + DIGEST), 2)
        self.assertIn(OTHER, rendered)
        first = self.kustomization.read_bytes()
        self.assert_success(self.edit())
        self.assertEqual(first, self.kustomization.read_bytes())
        self.assertIn("gitops/site-comemorativo/dev/apae-site-comemorativo", self.output.read_text())

    def test_separate_checkouts_preserve_local_action_and_scope_updates(self):
        self.assertEqual(AUTOMATION["with"].get("path", "."), ".")
        self.assertEqual(AUTOMATION["with"]["ref"], "${{ github.sha }}")
        self.assertEqual(AUTOMATION["with"]["token"], "${{ github.token }}")
        self.assertFalse(AUTOMATION["with"]["persist-credentials"])
        self.assertEqual(WORKFLOW["jobs"]["update-image"]["permissions"]["contents"], "read")
        self.assertEqual(MANIFESTS["with"]["ref"], "main")
        self.assertEqual(MANIFESTS["with"]["path"], "infra")
        self.assertEqual(MANIFESTS["with"]["token"], "${{ steps.app-token.outputs.token }}")
        self.assertFalse(MANIFESTS["with"]["persist-credentials"])
        local_step = next(step for step in STEPS if step.get("uses") == "./.github/actions/setup-kustomize")
        self.assertTrue((self.workspace / local_step["uses"] / "action.yml").is_file())
        self.assertFalse((self.manifests / ".github/actions/setup-kustomize").exists())
        self.assertLess(STEPS.index(AUTOMATION), STEPS.index(MANIFESTS))
        self.assertLess(STEPS.index(MANIFESTS), STEPS.index(local_step))

        before = {path.relative_to(self.workspace): path.read_bytes()
                  for path in self.workspace.rglob("*") if path.is_file()}
        self.assert_success(self.edit())
        after = {path.relative_to(self.workspace): path.read_bytes()
                 for path in self.workspace.rglob("*") if path.is_file() and path != self.output}
        changed = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
        self.assertEqual(changed, {self.kustomization.relative_to(self.workspace),
            Path("infra/releases/candidates/site-comemorativo") / (ENV["SOURCE_COMMIT"] + ".json")})

    def test_overlay_resolution_and_pr_paths_are_relative_to_main(self):
        result = subprocess.run(
            ["bash", "-c", OVERLAY_STEP["run"]], text=True, capture_output=True,
            cwd=self.workspace / OVERLAY_STEP["working-directory"],
            env={**os.environ, **ENV, "GITHUB_OUTPUT": str(self.output)},
        )
        self.assert_success(result)
        overlay = self.output.read_text().strip().removeprefix("path=")
        self.assertEqual(overlay, str(self.relative_overlay))
        config = PULL_REQUEST["with"]
        self.assertEqual(config["path"], MANIFESTS["with"]["path"])
        self.assertEqual(config["base"], "main")
        self.assertEqual(config["token"], "${{ steps.app-token.outputs.token }}")
        self.assertEqual(config["branch"], "${{ steps.image-update.outputs.branch }}")
        # Both exact paths are relative to the manifests checkout.
        self.assert_success(self.edit())
        candidate = f"releases/candidates/site-comemorativo/{ENV['SOURCE_COMMIT']}.json"
        paths = config["add-paths"].replace("${{ steps.overlay.outputs.path }}", overlay).replace(
            "${{ steps.image-update.outputs.candidate }}", candidate).splitlines()
        self.assertEqual(paths, [str(self.relative_overlay / "kustomization.yaml"), candidate])
        self.assertEqual(self.workspace / config["path"] / paths[0], self.kustomization)

    def test_replaces_tag_and_previous_digest(self):
        data = yaml.safe_load(self.kustomization.read_text())
        data["images"] = [{"name": IMAGE, "newTag": "sha-1234567", "digest": "sha256:" + "b" * 64}]
        self.kustomization.write_text(yaml.safe_dump(data))
        self.assert_success(self.edit())
        entry = yaml.safe_load(self.kustomization.read_text())["images"][0]
        self.assertEqual(entry["digest"], DIGEST)
        self.assertNotIn("newTag", entry)

    def test_resolves_only_paths_defined_in_pr_120(self):
        for application, path in (
            ("apae-geral", "kubernetes/apae-geral/overlays/dev"),
            ("apae-atendimento", "kubernetes/apae-atendimento/overlays/dev"),
            ("apae-gestao-escolar", "kubernetes/gestao-escolar/overlays/dev"),
            ("site-comemorativo", "kubernetes/site-comemorativo/overlays/dev"),
        ):
            with self.subTest(application=application):
                target = self.manifests / path
                target.mkdir(parents=True, exist_ok=True)
                (target / "kustomization.yaml").touch()
                self.output.unlink(missing_ok=True)
                result = subprocess.run(
                    ["bash", "-c", OVERLAY_STEP["run"]], text=True, capture_output=True,
                    cwd=self.manifests,
                    env={**os.environ, **ENV, "APPLICATION": application,
                         "GITHUB_OUTPUT": str(self.output)},
                )
                self.assert_success(result)
                self.assertEqual(self.output.read_text(), f"path={path}\n")

    def test_rejects_unknown_paths_and_environments(self):
        for overrides, message in (
            ({"APPLICATION": "../../etc"}, "Aplicação não autorizada"),
            ({"APPLICATION": "unknown"}, "Aplicação não autorizada"),
            ({"APPLICATION": "kubernetes/apae-geral/overlays/dev"}, "Aplicação não autorizada"),
            ({"ENVIRONMENT": "hml"}, "Somente dev"),
            ({"ENVIRONMENT": "prod"}, "Somente dev"),
        ):
            with self.subTest(overrides=overrides):
                self.output.unlink(missing_ok=True)
                result = subprocess.run(
                    ["bash", "-c", OVERLAY_STEP["run"]], text=True, capture_output=True,
                    cwd=self.manifests,
                    env={**os.environ, **ENV, **overrides, "GITHUB_OUTPUT": str(self.output)},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout)
                self.assertFalse(self.output.exists())

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
        before = self.kustomization.read_bytes()
        self.assertNotEqual(self.edit().returncode, 0)
        self.assertEqual(before, self.kustomization.read_bytes())

    def test_ambiguous_rules_fail_without_editing(self):
        data = yaml.safe_load(self.kustomization.read_text())
        data["images"] = [{"name": IMAGE, "newTag": "dev"},
                          {"name": IMAGE, "newTag": "other"}]
        self.kustomization.write_text(yaml.safe_dump(data))
        before = self.kustomization.read_bytes()
        self.assertNotEqual(self.edit().returncode, 0)
        self.assertEqual(before, self.kustomization.read_bytes())

    def test_new_receiver_run_preserves_original_candidate(self):
        self.assert_success(self.edit())
        candidate = self.manifests / "releases/candidates/site-comemorativo" / (ENV["SOURCE_COMMIT"] + ".json")
        before = candidate.read_bytes()
        self.assert_success(self.edit(VERIFICATION_RUN="https://github.com/IFPBEsp/APAE-INFRA/actions/runs/99"))
        self.assertEqual(candidate.read_bytes(), before)

    def test_existing_candidate_cannot_change_digest(self):
        self.assert_success(self.edit())
        before = self.kustomization.read_bytes()
        self.assertNotEqual(self.edit(IMAGE_DIGEST="sha256:" + "b" * 64).returncode, 0)
        self.assertEqual(self.kustomization.read_bytes(), before)


def embedded_python(step):
    return step["run"].split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]


class CompleteReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "outputs"
        self.release = ReleaseDispatchTest().valid_release()
        self.step = next(step for step in RELEASE_STEPS if step.get("id") == "release-update")

    def fixture(self, application="apae-geral", repository="IFPBEsp/APAE"):
        self.release.update(application=application, source_repository=repository,
                            workflow_run=f"https://github.com/{repository}/actions/runs/123456")
        for component, item in self.release["images"].items():
            item.update(image=f"ghcr.io/ifpbesp/{application}-{component}",
                        workflow_run=self.release["workflow_run"])
        self.path = self.root / "kubernetes" / ("gestao-escolar" if application == "apae-gestao-escolar" else application) / "overlays/dev/kustomization.yaml"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n- deployment.yaml\n")
        self.deployment = self.path.with_name("deployment.yaml")
        self.deployment.write_text(yaml.safe_dump({
            "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "test"},
            "spec": {"template": {"spec": {"containers": [
                {"name": component, "image": item["image"] + ":dev"}
                for component, item in self.release["images"].items()
            ] + [{"name": "unrelated", "image": "ghcr.io/other/service:dev"}]}}},
        }))
        return self.release

    def execute(self, step, **env):
        return subprocess.run([sys.executable, "-c", embedded_python(step)], cwd=self.root,
                              env={**os.environ, "RUNNER_TEMP": str(self.root),
                                   "GITHUB_OUTPUT": str(self.output), **env},
                              text=True, capture_output=True)

    def update(self):
        (self.root / "verified-release-input.json").write_text(json.dumps(self.release))
        return self.execute(self.step, APPLICATION=self.release["application"])

    def test_all_joint_products_validate_and_update_both_images_idempotently(self):
        for application, repository in (("apae-geral", "IFPBEsp/APAE"),
                                        ("apae-atendimento", "IFPBEsp/APAE-atendimento"),
                                        ("apae-gestao-escolar", "IFPBEsp/APAE-gestao-escolar")):
            with self.subTest(application=application):
                release = self.fixture(application, repository)
                dispatch, _ = ReleaseDispatchTest().validate(release)
                self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
                contract = self.execute(RELEASE_STEPS[0], RELEASE_JSON=json.dumps(release),
                    APPLICATION=application, SOURCE_REPOSITORY=repository,
                    SOURCE_COMMIT=release["source_commit"], ENVIRONMENT="dev",
                    CALLER_REPOSITORY="IFPBEsp/APAE-INFRA", SINGLE_IMAGE="", SINGLE_TAG="", SINGLE_DIGEST="")
                self.assertEqual(contract.returncode, 0, contract.stderr)
                result = self.update()
                self.assertEqual(result.returncode, 0, result.stderr)
                candidate = self.root / "releases/candidates" / application / (release["source_commit"] + ".json")
                self.assertEqual(json.loads(candidate.read_text()), release)
                rendered = subprocess.check_output(["kustomize", "build", str(self.path.parent)], text=True)
                for item in release["images"].values():
                    self.assertIn(item["image"] + "@" + item["digest"], rendered)
                self.assertIn("ghcr.io/other/service:dev", rendered)
                original = self.path.read_bytes(), candidate.read_bytes()
                self.assertEqual(self.update().returncode, 0)
                self.assertEqual((self.path.read_bytes(), candidate.read_bytes()), original)

    def test_missing_component_or_overlay_cannot_write_candidate(self):
        self.fixture()
        self.deployment.write_text(self.deployment.read_text().replace(
            self.release["images"]["frontend"]["image"], "ghcr.io/other/frontend"))
        before = self.path.read_bytes()
        self.assertNotEqual(self.update().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        self.assertNotEqual(self.update().returncode, 0)
        self.assertFalse((self.root / "releases").exists())

    def test_conflicting_candidate_restores_overlay_and_preserves_record(self):
        self.fixture()
        candidate = self.root / "releases/candidates/apae-geral" / (self.release["source_commit"] + ".json")
        candidate.parent.mkdir(parents=True)
        candidate.write_text('{"unexpected": true}\n')
        before = self.path.read_bytes(), candidate.read_bytes()
        self.assertNotEqual(self.update().returncode, 0)
        self.assertEqual((self.path.read_bytes(), candidate.read_bytes()), before)
        self.assertFalse(self.output.exists())

    def test_signature_checks_fail_closed_before_write_credentials(self):
        for steps, name, token in ((STEPS, "Verify published Cosign signature", "Generate GitHub App token"),
                                  (RELEASE_STEPS, "Verify both Cosign signatures", "Generate image updater GitHub App token")):
            self.fixture()
            (self.root / "verified-release-input.json").write_text(json.dumps(self.release))
            verifier = next(step for step in steps if step["name"] == name)
            names = [step["name"] for step in steps]
            self.assertLess(names.index(name), names.index(token))
            fake = self.root / "cosign"
            fake.write_text('#!/bin/sh\nexit "$COSIGN_EXIT"\n')
            fake.chmod(0o755)
            for exit_code in (0, 1):
                result = subprocess.run(["bash", "-c", verifier["run"]], cwd=self.root,
                    env={**os.environ, **ENV, "RUNNER_TEMP": str(self.root),
                         "PATH": str(self.root) + ":" + os.environ["PATH"], "COSIGN_EXIT": str(exit_code)},
                    text=True, capture_output=True)
                self.assertEqual(result.returncode == 0, exit_code == 0, result.stderr)
            for flag in ("--certificate-identity-regexp", "--certificate-oidc-issuer", "--certificate-github-workflow-sha"):
                self.assertIn(flag, verifier["run"])

    def test_verified_attestations_must_match_run_and_attempt(self):
        self.fixture()
        (self.root / "verified-release-input.json").write_text(json.dumps(self.release))
        fake = self.root / "gh"
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys
component = 'backend' if '-backend@' in ' '.join(sys.argv) else 'frontend'
if os.environ.get('VERIFY_FAIL') == component:
    raise SystemExit(1)
invocation = os.environ['INVOCATION_' + component.upper()]
print(json.dumps([{'verificationResult': {'statement': {'predicate': {
    'runDetails': {'metadata': {'invocationId': invocation}}}}}}]))
''')
        fake.chmod(0o755)
        verifier = next(step for step in RELEASE_STEPS if step["name"] == "Verify both build attestations")
        run = self.release["workflow_run"]
        for backend, frontend, failure, accepted in (
            (run + "/attempts/1", run + "/attempts/1", "", True),
            (run + "/attempts/1", run + "/attempts/2", "", False),
            (run + "/attempts/1", run.replace("123456", "999") + "/attempts/1", "", False),
            (run + "/attempts/1", "", "", False),
            (run + "/attempts/1", run + "/attempts/1", "frontend", False),
        ):
            result = subprocess.run(["bash", "-c", verifier["run"]], cwd=self.root,
                env={**os.environ, **ENV, "RUNNER_TEMP": str(self.root),
                     "PATH": str(self.root) + ":" + os.environ["PATH"],
                     "INVOCATION_BACKEND": backend, "INVOCATION_FRONTEND": frontend, "VERIFY_FAIL": failure},
                text=True, capture_output=True)
            self.assertEqual(result.returncode == 0, accepted, result.stderr)



class ProductionGatesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.infra = self.root / "approved-main"
        self.infra.mkdir()
        self.output = self.root / "outputs"
        self.workflows = {name: yaml.safe_load((ROOT / f".github/workflows/{name}-release.yml").read_text())
                          for name in ("approve", "promote", "rollback")}
        self.release = ReleaseDispatchTest().valid_release()

    def step(self, workflow, name):
        job = next(iter(self.workflows[workflow]["jobs"].values()))
        return next(step for step in job["steps"] if step.get("name") == name)

    def execute(self, workflow, name, cwd=None):
        return subprocess.run([sys.executable, "-c", embedded_python(self.step(workflow, name))],
            cwd=cwd or self.root, text=True, capture_output=True,
            env={**os.environ, "APPLICATION": self.release["application"],
                 "CANDIDATE_COMMIT": self.release["source_commit"], "RUNNER_TEMP": str(self.root),
                 "GITHUB_OUTPUT": str(self.output), "EVIDENCE_URL": "https://github.com/IFPBEsp/APAE/issues/106",
                 "APPROVAL_REASON": "Homologacao concluida com evidencia revisada",
                 "PROMOTION_REASON": "Promocao autorizada apos homologacao completa",
                 "ROLLBACK_REASON": "Rollback por regressao identificada em producao",
                 "APPROVER": "reviewer", "APPROVAL_RUN": "https://github.com/IFPBEsp/APAE-INFRA/actions/runs/55",
                 "PATH": str(self.root) + ":" + os.environ["PATH"]})

    def prepare_candidate(self):
        sha = self.release["source_commit"]
        application = self.release["application"]
        self.candidate = self.infra / "releases/candidates" / application / (sha + ".json")
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text(json.dumps(self.release, indent=2, sort_keys=True) + "\n")
        self.approval = self.infra / "releases/approved" / application / (sha + ".json")
        overlay = self.infra / "kubernetes" / ("gestao-escolar" if application == "apae-gestao-escolar" else application) / "overlays/dev/kustomization.yaml"
        overlay.parent.mkdir(parents=True)
        targets = self.release.get("images", {"site": self.release})
        overlay.write_text(yaml.safe_dump({"images": [{"name": item["image"], "digest": item["digest"]}
                                                     for item in targets.values()]}))
        return overlay

    def test_approval_promotion_and_rollback_records_support_all_products(self):
        products = (("apae-geral", "IFPBEsp/APAE"), ("apae-atendimento", "IFPBEsp/APAE-atendimento"),
                    ("apae-gestao-escolar", "IFPBEsp/APAE-gestao-escolar"),
                    ("site-comemorativo", "IFPBEsp/apae-site-comemorativo"))
        for application, repository in products:
            with self.subTest(application=application):
                self.release = ReleaseDispatchTest().valid_release()
                self.release.update(application=application, source_repository=repository,
                                    workflow_run=f"https://github.com/{repository}/actions/runs/123456")
                for component, item in self.release["images"].items():
                    item.update(image=f"ghcr.io/ifpbesp/{application}-{component}", workflow_run=self.release["workflow_run"])
                if application == "site-comemorativo":
                    self.release.pop("images")
                    self.release.update(image=IMAGE, tag=ENV["IMAGE_TAG"], digest=DIGEST,
                                        verification_run="https://github.com/IFPBEsp/APAE-INFRA/actions/runs/42")
                self.prepare_candidate()
                for workflow, step in (("promote", "Validate merged approval and candidate integrity"),
                                       ("rollback", "Validate approved release record")):
                    # A candidate alone cannot authorize a production change.
                    result = self.execute(workflow, step)
                    self.assertNotEqual(result.returncode, 0)
                result = self.execute("approve", "Validate candidate, deployed overlay intent and evidence", self.infra)
                self.assertEqual(result.returncode, 0, result.stderr)
                for workflow, step in (("promote", "Validate merged approval and candidate integrity"),
                                       ("rollback", "Validate approved release record")):
                    result = self.execute(workflow, step)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    original = self.candidate.read_bytes()
                    self.candidate.write_bytes(original + b" ")
                    self.assertNotEqual(self.execute(workflow, step).returncode, 0)
                    self.candidate.write_bytes(original)

    def test_approval_rejects_overlay_that_does_not_match_candidate(self):
        overlay = self.prepare_candidate()
        overlay.write_text(overlay.read_text().replace("a" * 64, "c" * 64))
        result = self.execute("approve", "Validate candidate, deployed overlay intent and evidence", self.infra)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.approval.exists())

    def test_rollback_requires_joint_digests_in_same_main_history_revision(self):
        self.prepare_candidate()
        self.assertEqual(self.execute("approve", "Validate candidate, deployed overlay intent and evidence", self.infra).returncode, 0)
        self.assertEqual(self.execute("rollback", "Validate approved release record").returncode, 0)
        production = self.root / "production"
        overlay = production / "kubernetes/apae-geral/overlays/prod/kustomization.yaml"
        overlay.parent.mkdir(parents=True)
        targets = self.release["images"]
        overlay.write_text(yaml.safe_dump({
            "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
            "resources": ["deployment.yaml"],
            "images": [{"name": item["image"], "digest": "sha256:" + "c" * 64} for item in targets.values()]}))
        overlay.with_name("deployment.yaml").write_text(yaml.safe_dump({
            "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "test"},
            "spec": {"template": {"spec": {"containers": [
                {"name": part, "image": item["image"] + ":dev"} for part, item in targets.items()]}}}}))
        fake_git = self.root / "git"
        fake_git.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
root = pathlib.Path(os.environ['RUNNER_TEMP'])
if sys.argv[1] == 'log':
    assert '--first-parent' in sys.argv and 'HEAD' in sys.argv
    print('d' * 40)
elif sys.argv[1] == 'show':
    sys.stdout.write((root / 'historical.yaml').read_text())
else:
    raise SystemExit(99)
''')
        fake_git.chmod(0o755)
        historical = self.root / "historical.yaml"
        initial = overlay.read_bytes()
        historical.write_bytes(initial)
        name = "Confirm historical production deployment and prepare rollback"
        self.assertNotEqual(self.execute("rollback", name, production).returncode, 0)
        self.assertEqual(overlay.read_bytes(), initial)
        history = yaml.safe_load(initial)
        # A partial historic release still cannot authorize rollback.
        history["images"][0]["digest"] = targets["backend"]["digest"]
        historical.write_text(yaml.safe_dump(history))
        self.assertNotEqual(self.execute("rollback", name, production).returncode, 0)
        history["images"][1]["digest"] = targets["frontend"]["digest"]
        historical.write_text(yaml.safe_dump(history))
        result = self.execute("rollback", name, production)
        self.assertEqual(result.returncode, 0, result.stderr)
        applied = yaml.safe_load(overlay.read_text())["images"]
        self.assertEqual([item["digest"] for item in applied], [item["digest"] for item in targets.values()])

    def test_production_workflows_do_not_build_or_publish_images(self):
        for name, workflow in self.workflows.items():
            job = next(iter(workflow["jobs"].values()))
            self.assertEqual(job["environment"], "release-approval" if name == "approve" else "production-promotion")
            for step in job["steps"]:
                self.assertNotIn("docker/build-push-action", step.get("uses", ""))
                self.assertNotRegex(step.get("run", ""), r"docker (build|push)|cosign sign")


if __name__ == "__main__":
    unittest.main()
