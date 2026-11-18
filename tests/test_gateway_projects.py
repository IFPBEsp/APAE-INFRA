"""Guard the trust boundary between bootstrap Applications and Gateway workloads."""

from pathlib import Path
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

    def test_root_and_gateway_applications_use_their_own_projects(self):
        self.assertEqual(load('argocd/app-of-apps.yaml')['spec']['project'], 'apae-infra')
        applications = list((ROOT / 'argocd/apps/infra').glob('*.yaml'))
        self.assertEqual(len(applications), 3)
        for path in applications:
            app = yaml.safe_load(path.read_text())
            with self.subTest(application=app['metadata']['name']):
                self.assertEqual(app['spec']['project'], 'apae-gateway')
                self.assertIn(app['spec']['source']['repoURL'], self.gateway['spec']['sourceRepos'])
                self.assertIn(app['spec']['destination'], self.gateway['spec']['destinations'])
                self.assertFalse(app['spec'].get('syncPolicy', {}).get('automated'))

    def test_bootstrap_applies_projects_before_the_root(self):
        tasks = load('ansible/roles/argocd_bootstrap/tasks/bootstrap.yml')
        bootstrap = next(task for task in tasks if 'loop' in task)['loop']
        for project in ('project-infra.yaml', 'project-gateway.yaml'):
            self.assertLess(bootstrap.index(project), bootstrap.index('app-of-apps.yaml'))


if __name__ == '__main__':
    unittest.main()
