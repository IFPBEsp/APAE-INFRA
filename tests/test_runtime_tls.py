"""Exercise rendered TLS scripts with isolated Docker/systemd/network doubles.

No SSH, Docker daemon, ACME request or host service is used. Behaviour tests
replace only the EUID guard in their temporary script; a separate test checks
that the unmodified guard refuses an unprivileged caller.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "ansible/roles/runtime_mode/templates"
VARIABLES = ROOT / "ansible/inventories/production/group_vars/production.yml"

DRIVER = r'''#!/usr/bin/python3
import json, os, shutil, sys, time
from pathlib import Path
p = Path(os.environ["MOCK_STATE"])
s = json.loads(p.read_text())
tool, args = Path(sys.argv[0]).name, sys.argv[1:]
s["events"].append([tool, *args])
def save(): p.write_text(json.dumps(s))
def finish(code=0, text=""):
    save()
    if text: print(text)
    raise SystemExit(code)
if tool == "systemctl": finish(text=s.get("cluster", "inactive"))
if tool == "pgrep": finish(0 if s.get("shims") else 1)
if tool == "ss": finish(text="LISTEN :80" if s.get("foreign_port") else "")
if tool == "curl": finish(1 if s.get("curl_failure") else 0)
if tool == "docker":
    if args[:2] == ["image", "inspect"]: finish(1 if s.get("missing_image") else 0)
    if args[0] == "ps":
        if "--all" in args: finish(text="certbot-id" if s.get("certbot") else "")
        if "publish=80/tcp" in args: finish(text="foreign-id" if s.get("foreign_container") else "")
        finish(text="proxy-id" if s["proxy"] else "")
    if args[0] == "stop":
        assert args[-1] == "proxy-proxy-1", "attempt to stop data service"
        s["proxy"] = False
        finish()
    if args[0] == "start":
        assert args[-1] == "proxy-proxy-1", "attempt to start data service"
        if s.get("restore_failure"): finish(1)
        s["proxy"] = True
        finish()
    if args[0] == "rm":
        s["certbot"] = False
        finish()
    if args[0] == "run":
        assert "--pull" in args and args[args.index("--pull") + 1] == "never"
        s["certbot"] = True
        save()
        if s.get("slow"): time.sleep(5)
        if s.get("renew_failure"): finish(23)
        if "--dry-run" not in args and not s.get("no_renewal"):
            shutil.copyfile(s["new_certificate"], s["certificate"])
        s["certbot"] = False
        finish()
finish(2)
'''


class RuntimeTlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.certificates = {}
        for name, days in (("soon", 1), ("fresh", 7), ("renewed", 8)):
            cert = Path(cls.fixtures.name) / f"{name}.pem"
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt",
                "ec_paramgen_curve:P-256", "-nodes", "-days", str(days),
                "-subj", "/CN=127.0.0.1", "-out", str(cert),
                "-keyout", str(cert.with_suffix(".key")),
            ], check=True, capture_output=True)
            cls.certificates[name] = cert
        expired = Path(cls.fixtures.name) / "expired.pem"
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "127.0.0.1")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(days=2))
                       .not_valid_after(now - timedelta(days=1)).sign(key, hashes.SHA256()))
        expired.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        cls.certificates["expired"] = expired

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)
        self.lock = self.path / "lock"
        self.lock.mkdir()
        self.cert = self.path / "certificate.pem"
        shutil.copyfile(self.certificates["soon"], self.cert)
        config = self.path / "config"
        (config / "renewal").mkdir(parents=True)
        (config / "renewal/143.95.170.25.conf").touch()
        for directory in ("work", "logs", "bin"):
            (self.path / directory).mkdir()
        self.state_file = self.path / "mode"
        self.state_file.write_text("compose\n")
        self.mock_state = self.path / "state.json"
        self.mock_state.write_text(json.dumps({
            "events": [], "proxy": True, "certificate": str(self.cert),
            "new_certificate": str(self.certificates["renewed"]),
        }))
        driver = self.path / "driver"
        driver.write_text(DRIVER)
        driver.chmod(0o700)
        for tool in ("docker", "systemctl", "pgrep", "ss", "curl"):
            (self.path / "bin" / tool).symlink_to(driver)
        self.values = yaml.safe_load(VARIABLES.read_text())
        self.values.update({
            "runtime_mode_lock_directory": str(self.lock),
            "runtime_mode_state_file": str(self.state_file),
            "runtime_mode_compose_tls_certificate": str(self.cert),
            "runtime_mode_certbot_config_directory": str(config),
            "runtime_mode_certbot_work_directory": str(self.path / "work"),
            "runtime_mode_certbot_log_directory": str(self.path / "logs"),
            "runtime_mode_tls_core_script": str(self.path / "core"),
            "runtime_mode_tls_wrapper_script": str(self.path / "wrapper"),
        })
        self.render()

    def render(self):
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters["quote"] = lambda value: shlex.quote(str(value))
        for template, name in (("renew-compose-tls.sh.j2", "core"),
                               ("renew-compose-tls-wrapper.sh.j2", "wrapper")):
            code = env.from_string((TEMPLATES / template).read_text()).render(self.values)
            guard = '[[ "$EUID" -eq 0 ]]'
            self.assertEqual(code.count(guard), 1)
            original = self.path / f"{name}-original"
            original.write_text(code)
            code = code.replace(guard, '[[ 0 -eq 0 ]]', 1)
            path = self.path / name
            path.write_text(code)
            path.chmod(0o700)
            subprocess.run(["bash", "-n", str(path)], check=True)

    def update(self, **values):
        state = self.state()
        state.update(values)
        self.mock_state.write_text(json.dumps(state))

    def state(self):
        return json.loads(self.mock_state.read_text())

    def run_script(self, name="core", operation="--renew"):
        result = subprocess.run(["bash", str(self.path / name), operation],
                                capture_output=True, text=True, timeout=15,
                                env={**os.environ, "MOCK_STATE": str(self.mock_state),
                                     "PATH": str(self.path / "bin") + os.pathsep + os.environ["PATH"]})
        return result

    def events(self, tool="docker", action=None):
        return [event for event in self.state()["events"]
                if event[0] == tool and (action is None or event[1] == action)]

    def test_fresh_certificate_does_not_interrupt_proxy(self):
        shutil.copyfile(self.certificates["fresh"], self.cert)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TLS_UNCHANGED", result.stdout)
        self.assertEqual(self.events(), [])

    def test_due_certificate_is_renewed_and_proxy_restored(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TLS_RENEWED", result.stdout)
        self.assertTrue(self.state()["proxy"])
        self.assertEqual(len(self.events(action="stop")), 1)
        self.assertEqual(len(self.events(action="start")), 1)

    def test_expired_certificate_can_be_recovered(self):
        shutil.copyfile(self.certificates["expired"], self.cert)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TLS_RENEWED", result.stdout)

    def test_malformed_certificate_does_not_stop_proxy(self):
        self.cert.write_text("invalid certificate")
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.events(action="stop"), [])

    def test_transition_does_not_start_a_previously_stopped_proxy(self):
        self.update(proxy=False)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state()["proxy"])
        self.assertEqual(self.events(action="start"), [])

    def test_renewal_failure_cleans_certbot_and_restores_proxy(self):
        self.update(renew_failure=True)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state()["proxy"])
        self.assertFalse(self.state()["certbot"])

    def test_timeout_restores_proxy_and_cleans_container(self):
        self.values["runtime_mode_tls_renew_timeout_seconds"] = 1
        self.render()
        self.update(slow=True)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state()["proxy"])
        self.assertFalse(self.state()["certbot"])

    def test_restore_failure_is_not_reported_as_success(self):
        self.update(restore_failure=True)
        self.assertNotEqual(self.run_script().returncode, 0)

    def test_foreign_listener_aborts_and_restores_proxy(self):
        for field in ("foreign_port", "foreign_container"):
            with self.subTest(field=field):
                self.update(**{field: True})
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertTrue(self.state()["proxy"])
                self.assertEqual(self.events(action="run"), [])
                self.update(**{field: False})

    def test_cluster_or_remaining_shims_block_renewal(self):
        for values in ({"cluster": "active"}, {"shims": True}):
            with self.subTest(values=values):
                self.update(**{"cluster": "inactive", "shims": False, **values})
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertEqual(self.events(action="stop"), [])

    def test_missing_image_or_existing_certbot_preserves_proxy(self):
        for field in ("missing_image", "certbot"):
            with self.subTest(field=field):
                self.update(**{field: True})
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertEqual(self.events(action="stop"), [])
                self.update(**{field: False})

    def test_dry_run_uses_staging_and_preserves_certificate(self):
        before = self.cert.read_bytes()
        result = self.run_script(operation="--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TLS_DRY_RUN_OK", result.stdout)
        self.assertEqual(before, self.cert.read_bytes())
        self.assertIn("--dry-run", self.events(action="run")[0])

    def test_data_container_cannot_be_selected_as_proxy(self):
        self.values["runtime_mode_compose_proxy_container"] = "apae-postgres"
        self.render()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.events(action="stop"), [])

    def test_timer_defers_without_removing_existing_lock(self):
        result = self.run_script("wrapper", "--timer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.lock.is_dir())
        self.assertIn("TLS_DEFERRED", result.stdout)
        self.assertEqual(self.events(), [])

    def test_timer_defers_in_cluster_mode_and_releases_own_lock(self):
        self.lock.rmdir()
        self.state_file.write_text("cluster\n")
        result = self.run_script("wrapper", "--timer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.lock.exists())
        self.assertIn("TLS_DEFERRED", result.stdout)
        self.assertEqual(self.events(), [])

    def test_wrapper_renews_checks_https_and_releases_lock(self):
        self.lock.rmdir()
        result = self.run_script("wrapper", "--renew")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.lock.exists())
        self.assertTrue(self.state()["proxy"])
        self.assertEqual(len(self.events(tool="curl")), 1)

    def test_wrapper_releases_lock_when_certificate_renewal_fails(self):
        self.lock.rmdir()
        self.update(renew_failure=True)
        self.assertNotEqual(self.run_script("wrapper").returncode, 0)
        self.assertFalse(self.lock.exists())
        self.assertTrue(self.state()["proxy"])

    def test_https_failure_is_reported_and_lock_is_released(self):
        self.lock.rmdir()
        self.update(curl_failure=True)
        self.assertNotEqual(self.run_script("wrapper").returncode, 0)
        self.assertFalse(self.lock.exists())
        self.assertTrue(self.state()["proxy"])

    def test_timer_checks_actual_cluster_state(self):
        self.lock.rmdir()
        self.update(cluster="active")
        result = self.run_script("wrapper", "--timer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TLS_DEFERRED", result.stdout)
        self.assertFalse(self.lock.exists())
        self.assertEqual(self.events(), [])

    @unittest.skipIf(os.geteuid() == 0, "Requires unprivileged caller")
    def test_unmodified_script_rejects_non_root(self):
        result = self.run_script("wrapper-original")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.events(), [])


if __name__ == "__main__":
    unittest.main()
