"""Exercise the workflow's own scripts against disposable Kustomize fixtures."""

import base64
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
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
UPDATE = next(step["run"] for step in STEPS if step.get("id") == "image-update")
# Execute the Python embedded in the actual workflow, without its virtualenv wrapper.
EDITOR = UPDATE.split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]
REGISTRY_SCRIPT = next(step["run"] for step in STEPS if step.get("id") == "registry")
REGISTRY_CODE = REGISTRY_SCRIPT.split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]
REGISTRY = {"__name__": "registry_test"}
exec(compile(REGISTRY_CODE, "workflow:registry", "exec"), REGISTRY)
DISPATCH = yaml.safe_load((ROOT / ".github/workflows/update-image-overlay-dispatch.yml").read_text())
PAYLOAD_SCRIPT = DISPATCH["jobs"]["validate-payload"]["steps"][0]["run"]
SETUP = yaml.safe_load((ROOT / ".github/actions/setup-kustomize/action.yml").read_text())
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

    def test_all_known_services_are_allowed(self):
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
                    self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_overlay_reports_issue_92(self):
        script = next(step["run"] for step in STEPS if step.get("id") == "overlay")
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(["bash", "-c", script], cwd=directory,
                                    env={**os.environ, **ENV}, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue #92", result.stdout)


class DispatchTest(unittest.TestCase):
    def payload(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            result = subprocess.run(
                ["bash", "-c", PAYLOAD_SCRIPT], text=True, capture_output=True,
                env={**os.environ, "PAYLOAD": json.dumps(payload), "GITHUB_OUTPUT": str(output)},
            )
            return result, output.read_text() if output.exists() else ""

    def valid_payload(self):
        return {"application": ENV["APPLICATION"], "image": IMAGE,
                "image_tag": ENV["IMAGE_TAG"], "image_digest": DIGEST,
                "source_repository": ENV["SOURCE_REPOSITORY"], "source_commit": ENV["SOURCE_COMMIT"]}

    def test_default_environment_only_when_omitted(self):
        result, output = self.payload(self.valid_payload())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("environment=dev\n", output)
        for value in (None, False, 0, "", [], {}, "hml", "prod", "DEV"):
            with self.subTest(value=value):
                result, output = self.payload({**self.valid_payload(), "environment": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")

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
                self.assertEqual(scope, ["repository:ifpbesp/apae-geral-backend:pull"])
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
        rendered = subprocess.check_output(["kustomize", "build", str(self.path)], text=True)
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
