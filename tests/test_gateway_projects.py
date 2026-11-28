"""Guard the trust boundary between bootstrap Applications and Gateway workloads."""

from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVER = 'https://kubernetes.default.svc'
REPOSITORY = 'https://github.com/IFPBEsp/APAE-INFRA.git'


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


def permits(project, group, kind, namespace=None):
    spec = project['spec']
    if namespace is None:
        whitelist = spec['clusterResourceWhitelist']
    else:
        if {'server': SERVER, 'namespace': namespace} not in spec['destinations']:
            return False
        whitelist = spec['namespaceResourceWhitelist']
    return {'group': group, 'kind': kind} in whitelist or any(
        item['group'] in (group, '*') and item['kind'] in (kind, '*')
        for item in whitelist
    )


class GatewayProjectBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.infra = load('argocd/project-infra.yaml')
        self.gateway = load('argocd/project-gateway.yaml')
        self.cert_manager = load('argocd/project-cert-manager.yaml')

    def test_root_can_register_applications_but_cannot_deploy_workloads(self):
        spec = self.infra['spec']
        self.assertEqual(spec['sourceRepos'], [REPOSITORY])
        self.assertEqual(spec['destinations'], [{'server': SERVER, 'namespace': 'argocd'}])
        self.assertEqual(spec['clusterResourceWhitelist'], [])
        self.assertEqual(spec['namespaceResourceWhitelist'], [
            {'group': 'argoproj.io', 'kind': 'Application'},
        ])
        self.assertTrue(permits(self.infra, 'argoproj.io', 'Application', 'argocd'))
        for group, kind in [('apps', 'Deployment'), ('', 'ServiceAccount'),
                            ('batch', 'Job'), ('rbac.authorization.k8s.io', 'Role'),
                            ('rbac.authorization.k8s.io', 'RoleBinding')]:
            with self.subTest(kind=kind):
                self.assertFalse(permits(self.infra, group, kind, 'argocd'))

    def test_gateway_cannot_manage_argocd_or_register_applications(self):
        self.assertEqual(self.gateway['spec']['destinations'], [
            {'server': SERVER, 'namespace': 'nginx-gateway'},
        ])
        for resource in self.gateway['spec']['namespaceResourceWhitelist']:
            with self.subTest(resource=resource):
                self.assertFalse(permits(self.gateway, resource['group'], resource['kind'], 'argocd'))
        self.assertFalse(permits(self.gateway, 'argoproj.io', 'Application', 'nginx-gateway'))
        self.assertTrue(permits(self.gateway, 'apps', 'Deployment', 'nginx-gateway'))
        self.assertTrue(permits(self.gateway, 'rbac.authorization.k8s.io', 'RoleBinding', 'nginx-gateway'))

    def test_root_and_infrastructure_applications_use_their_own_projects(self):
        self.assertEqual(load('argocd/app-of-apps.yaml')['spec']['project'], 'apae-infra')
        expected_projects = {
            'gateway-api-crds': self.gateway,
            'nginx-gateway-fabric': self.gateway,
            'nginx-gateway': self.gateway,
            'cert-manager': self.cert_manager,
        }
        applications = sorted((ROOT / 'argocd/apps/infra').glob('*.yaml'))
        self.assertEqual({path.stem for path in applications}, set(expected_projects))
        for path in applications:
            app = yaml.safe_load(path.read_text())
            project = expected_projects[path.stem]
            with self.subTest(application=app['metadata']['name']):
                self.assertEqual(app['spec']['project'], project['metadata']['name'])
                self.assertIn(app['spec']['source']['repoURL'], project['spec']['sourceRepos'])
                self.assertIn(app['spec']['destination'], project['spec']['destinations'])
                self.assertFalse(app['spec'].get('syncPolicy', {}).get('automated'))

    def test_tls_keeps_solver_on_http_and_only_serves_the_production_certificate(self):
        overlays = ROOT / 'kubernetes/infra/nginx-gateway-tls'
        staging = subprocess.check_output(['kustomize', 'build', str(overlays / 'staging')], text=True)
        production = subprocess.check_output(['kustomize', 'build', str(overlays / 'production')], text=True)
        staging_resources = list(yaml.safe_load_all(staging))
        staging_gateway = next(resource for resource in staging_resources if resource['kind'] == 'Gateway')
        self.assertEqual([listener['name'] for listener in staging_gateway['spec']['listeners']], ['http'])
        self.assertFalse(any(resource['kind'] == 'HTTPRoute' for resource in staging_resources))

        resources = {
            (resource['kind'], resource['metadata']['name']): resource['spec']
            for resource in yaml.safe_load_all(production)
        }
        listeners = {listener['name']: listener for listener in resources['Gateway', 'apae-gateway']['listeners']}
        redirect = resources['HTTPRoute', 'apae-http-redirect']
        self.assertEqual(listeners['http']['port'], 80)
        self.assertEqual(listeners['http']['allowedRoutes']['namespaces']['from'], 'Same')
        self.assertEqual(redirect['parentRefs'], [{'name': 'apae-gateway', 'sectionName': 'http'}])
        self.assertEqual(redirect['rules'][0]['matches'], [{'path': {'type': 'PathPrefix', 'value': '/'}}])
        self.assertEqual(redirect['rules'][0]['filters'], [
            {'type': 'RequestRedirect', 'requestRedirect': {'scheme': 'https', 'statusCode': 302}},
        ])
        staging_cert = resources['Certificate', 'apae-staging-tls']
        public_cert = resources['Certificate', 'apae-public-tls']
        self.assertNotEqual(staging_cert['secretName'], public_cert['secretName'])
        self.assertEqual(listeners['https']['tls']['certificateRefs'][0]['name'], public_cert['secretName'])
        self.assertEqual(staging_cert['dnsNames'], public_cert['dnsNames'])
        self.assertEqual(public_cert['dnsNames'], [listeners['https']['hostname']])
        self.assertEqual(public_cert['dnsNames'], redirect['hostnames'])
        for name in (staging_cert['issuerRef']['name'], public_cert['issuerRef']['name']):
            with self.subTest(issuer=name):
                solver = resources['Issuer', name]['acme']['solvers'][0]['http01']['gatewayHTTPRoute']
                self.assertEqual(solver['parentRefs'][0]['sectionName'], 'http')
                self.assertEqual(solver['parentRefs'][0]['name'], 'apae-gateway')
                self.assertEqual(solver['serviceType'], 'ClusterIP')

    def test_bootstrap_applies_projects_before_the_root(self):
        tasks = load('ansible/roles/argocd_bootstrap/tasks/bootstrap.yml')
        bootstrap = next(task for task in tasks if 'loop' in task)['loop']
        for project in ('project-infra.yaml', 'project-gateway.yaml', 'project-cert-manager.yaml'):
            self.assertLess(bootstrap.index(project), bootstrap.index('app-of-apps.yaml'))


if __name__ == '__main__':
    unittest.main()
