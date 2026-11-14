"""Protocolo real del laboratorio. Publica commits y modifica solo gitops-clase."""
import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:14590'


def state():
    with urllib.request.urlopen(BASE + '/api/state', timeout=10) as response:
        return json.load(response)


def wait_for(description, predicate, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sample = state()
        if sample.get('actionError'):
            raise RuntimeError(sample['actionError'])
        if sample.get('connected') and not sample.get('busy') and predicate(sample):
            print('OK: ' + description, flush=True)
            return sample
        time.sleep(1)
    raise RuntimeError('Tiempo agotado: ' + description + '\n' + json.dumps(sample, ensure_ascii=False))


def action(name):
    request = urllib.request.Request(BASE + '/api/action', method='POST',
        headers={'Content-Type': 'application/json', 'X-Demo-Action': '1'},
        data=json.dumps({'action': name}).encode())
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 202
    time.sleep(0.5)


def steady(sample, replicas):
    return sample['git']['replicas'] == replicas and sample['cluster']['target'] == replicas and sample['cluster']['ready'] == replicas and sample['argo']['sync'] == 'Synced' and sample['argo']['health'] == 'Healthy'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='output/evidencia.json')
    args = parser.parse_args()
    result = {'startedAt': datetime.now(timezone.utc).isoformat(), 'checks': [], 'samples': {}}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        action('reset')
        initial = wait_for('Estado inicial: Git=2, Deployment=2, Ready=2, Synced y Healthy', lambda s: steady(s, 2))
        result['samples']['initial'] = initial
        result['checks'].append('initial_two_replicas')
        action('publish-three')
        updated = wait_for('Commit Git despliega tres replicas mediante Argo CD', lambda s: steady(s, 3) and s['argo']['revision'] == s['git']['commit'])
        assert initial['git']['commit'] != updated['git']['commit']
        result['samples']['git_three'] = updated
        result['checks'].extend(['new_commit_pushed', 'argo_deployed_same_revision', 'three_ready'])
        commit = updated['git']['commit']
        action('drift-without-heal')
        drift = wait_for('Sin selfHeal: Git=3, Deployment=2, Ready=2 y OutOfSync', lambda s: s['git']['replicas'] == 3 and s['cluster']['target'] == 2 and s['cluster']['ready'] == 2 and not s['argo']['selfHeal'] and s['argo']['sync'] == 'OutOfSync')
        assert drift['git']['commit'] == commit
        result['samples']['drift_without_heal'] = drift
        result['checks'].append('manual_drift_without_git_change')
        for _ in range(6):
            time.sleep(1)
            sample = state()
            assert sample['connected'] and sample['cluster']['target'] == 2 and not sample['argo']['selfHeal']
        result['checks'].append('drift_persists_without_self_heal')
        action('enable-heal')
        healed = wait_for('selfHeal restaura tres replicas conservando el commit', lambda s: steady(s, 3) and s['argo']['selfHeal'] and s['git']['commit'] == commit)
        result['samples']['healed'] = healed
        result['checks'].append('argo_self_heal_restores_git_state')
        action('drift-with-heal')
        # Dar tiempo al sondeo para ver el cambio y la reconciliacion del controlador.
        time.sleep(3)
        healed_again = wait_for('Segundo cambio manual corregido con selfHeal activo', lambda s: steady(s, 3) and s['argo']['selfHeal'] and s['git']['commit'] == commit)
        result['samples']['healed_again'] = healed_again
        result['checks'].append('active_self_heal_corrects_second_drift')
        with urllib.request.urlopen('http://127.0.0.1:14500/pod.json', timeout=10) as response:
            assert response.status == 200
            served_pod = json.load(response)['pod']
        assert served_pod.startswith('hola-gitops-')
        result['http'] = {'status': 200, 'pod': served_pod}
        result['checks'].append('application_http_200_from_real_pod')
        action('reset')
        result['samples']['reset'] = wait_for('Laboratorio preparado para otra toma: dos replicas', lambda s: steady(s, 2) and s['argo']['selfHeal'])
        result['checks'].append('reset_via_git')
        result['passed'] = True
    except Exception as error:
        result.update(passed=False, error=str(error))
        raise
    finally:
        result['finishedAt'] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Resultado: {len(result['checks'])} comprobaciones aprobadas. {output}")


if __name__ == '__main__':
    main()
