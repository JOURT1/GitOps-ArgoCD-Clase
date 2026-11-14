"""Panel de un laboratorio REAL. Observa kubectl y Git; nunca reconcilia replicas.
Las unicas escrituras son las acciones explicitas del presentador.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
KUBECONFIG = LOCAL / 'kubeconfig'
REPOSITORY = 'https://github.com/JOURT1/GitOps-ArgoCD-Clase'
STATE_LOCK = threading.RLock()
ACTION_LOCK = threading.Lock()
EVENTS: list[dict] = []
STATE: dict = {'connected': False, 'error': 'Leyendo el laboratorio...', 'busy': False, 'events': []}
GIT_STATE: dict = {}
LAST_FETCH = 0.0
LAST_SIGNATURE = None


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def run(args, timeout=30):
    process = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                             errors='replace', timeout=timeout,
                             env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'})
    if process.returncode:
        detail = (process.stderr or process.stdout).strip()[-1500:]
        raise RuntimeError(detail or f'El comando termino con codigo {process.returncode}')
    return process.stdout.rstrip('\r\n')


def kubectl(*args, json_result=False):
    output = run(['kubectl', '--kubeconfig', str(KUBECONFIG), '--context', 'kind-gitops-clase', *args])
    return json.loads(output) if json_result else output


def event(message, kind='info'):
    item = {'at': now(), 'message': message, 'kind': kind}
    with STATE_LOCK:
        EVENTS.append(item)
        del EVENTS[:-80]
    LOCAL.mkdir(exist_ok=True)
    with (LOCAL / 'eventos.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + '\n')


def git_info(fetch=False):
    if fetch:
        run(['git', 'fetch', '--quiet', 'origin', 'main'])
    manifest = run(['git', 'show', 'refs/remotes/origin/main:k8s/deployment.yaml'])
    match = re.search(r'^  replicas: ([23])$', manifest, re.MULTILINE)
    if not match:
        raise RuntimeError('El manifiesto remoto no declara 2 o 3 replicas como espera esta practica.')
    commit = run(['git', 'rev-parse', 'refs/remotes/origin/main'])
    return {'replicas': int(match[1]), 'commit': commit,
            'message': run(['git', 'log', '-1', '--format=%s', 'refs/remotes/origin/main']),
            'repository': REPOSITORY, 'file': REPOSITORY + '/blob/main/k8s/deployment.yaml'}


def snapshot():
    global GIT_STATE, LAST_FETCH, LAST_SIGNATURE
    if not GIT_STATE or (time.monotonic() - LAST_FETCH > 10 and not ACTION_LOCK.locked()):
        GIT_STATE = git_info(fetch=True)
        LAST_FETCH = time.monotonic()
    resources = kubectl('-n', 'demo-clase', 'get', 'deployments,pods', '-o', 'json', json_result=True)
    app = kubectl('-n', 'argocd', 'get', 'application', 'hola-gitops', '-o', 'json', json_result=True)
    deployment = next(x for x in resources['items'] if x['kind'] == 'Deployment' and x['metadata']['name'] == 'hola-gitops')
    pods = []
    for resource in resources['items']:
        if resource['kind'] != 'Pod' or resource['metadata'].get('labels', {}).get('app') != 'hola-gitops':
            continue
        ready = any(c['type'] == 'Ready' and c['status'] == 'True' for c in resource.get('status', {}).get('conditions', []))
        pods.append({'name': resource['metadata']['name'], 'uid': resource['metadata']['uid'],
                     'ready': ready, 'phase': resource.get('status', {}).get('phase', 'Unknown'),
                     'terminating': bool(resource['metadata'].get('deletionTimestamp'))})
    app_status = app.get('status', {})
    automated = app['spec']['syncPolicy'].get('automated', {})
    current = {'target': deployment['spec']['replicas'],
               'ready': deployment.get('status', {}).get('readyReplicas', 0),
               'available': deployment.get('status', {}).get('availableReplicas', 0),
               'pods': sorted(pods, key=lambda p: p['name'])}
    argo = {'sync': app_status.get('sync', {}).get('status', 'Unknown'),
            'health': app_status.get('health', {}).get('status', 'Unknown'),
            'revision': app_status.get('sync', {}).get('revision', ''),
            'selfHeal': automated.get('selfHeal', False), 'autoSync': automated.get('enabled', True),
            'operation': app_status.get('operationState', {}).get('phase', ''),
            'conditions': app_status.get('conditions', []),
            'reconciledAt': app_status.get('reconciledAt'), 'url': 'http://127.0.0.1:14580/applications/argocd/hola-gitops'}
    signature = (GIT_STATE['replicas'], current['target'], current['ready'], argo['sync'], argo['selfHeal'])
    if signature != LAST_SIGNATURE:
        event(f"Git: {GIT_STATE['replicas']} | Deployment: {current['target']} | Ready: {current['ready']} | {argo['sync']} | selfHeal: {argo['selfHeal']}", 'state')
        LAST_SIGNATURE = signature
    return {'connected': True, 'updatedAt': now(), 'git': dict(GIT_STATE), 'cluster': current, 'argo': argo,
            'appUrl': 'http://127.0.0.1:14500', 'context': 'kind-gitops-clase', 'namespace': 'demo-clase'}


def poll():
    while True:
        try:
            current = snapshot()
            with STATE_LOCK:
                STATE.update(current)
                STATE.pop('error', None)
        except Exception as error:
            with STATE_LOCK:
                STATE.update(connected=False, error=str(error))
        time.sleep(0.7)


def policy(heal):
    patch = json.dumps({'spec': {'syncPolicy': {'automated': {'enabled': True, 'prune': True, 'selfHeal': heal}}}})
    kubectl('-n', 'argocd', 'patch', 'application', 'hola-gitops', '--type', 'merge', '-p', patch)
    event('selfHeal activado. Argo CD puede corregir los desvios.' if heal else 'selfHeal desactivado para observar el desvio. Auto-sync sigue habilitado.', 'action')


def publish(replicas):
    global GIT_STATE, LAST_FETCH
    branch = run(['git', 'branch', '--show-current'])
    if branch != 'main':
        raise RuntimeError('Este laboratorio solo publica desde la rama main.')
    run(['git', 'fetch', '--quiet', 'origin', 'main'])
    remote = run(['git', 'rev-parse', 'origin/main'])
    if run(['git', 'merge-base', '--is-ancestor', remote, 'HEAD']) != '':
        raise RuntimeError('Hay cambios remotos pendientes. Revisa Git antes de publicar.')
    changes = run(['git', 'status', '--porcelain', '--untracked-files=no'])
    if changes and any(line[3:] != 'k8s/deployment.yaml' for line in changes.splitlines()):
        raise RuntimeError('Hay cambios locales ajenos al manifiesto. Guardalos antes de ejecutar la actividad.')
    path = ROOT / 'k8s' / 'deployment.yaml'
    text = path.read_text(encoding='utf-8')
    updated, count = re.subn(r'^  replicas: [23]$', f'  replicas: {replicas}', text, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError('El manifiesto no tiene la estructura esperada.')
    path.write_text(updated, encoding='utf-8', newline='\n')
    run(['git', 'add', '--', 'k8s/deployment.yaml'])
    if run(['git', 'diff', '--cached', '--name-only']):
        run(['git', 'commit', '-m', f'demo: declarar {replicas} replicas en Git'])
    run(['git', 'push', 'origin', 'main'], timeout=60)
    GIT_STATE = git_info()
    LAST_FETCH = time.monotonic()
    event(f"Commit {GIT_STATE['commit'][:8]} publicado en GitHub: replicas={replicas}. Esperando a Argo CD; el panel no aplica el Deployment.", 'git')


def do_action(name):
    try:
        if name == 'publish-three':
            policy(True)
            publish(3)
        elif name == 'drift-without-heal':
            with STATE_LOCK:
                ready = STATE.get('connected') and STATE.get('git', {}).get('replicas') == 3 and STATE.get('cluster', {}).get('target') == 3 and STATE.get('cluster', {}).get('ready') == 3 and STATE.get('argo', {}).get('sync') == 'Synced'
            if not ready:
                raise RuntimeError('Primero espera a que Git y el cluster tengan 3 replicas listas y estado Synced.')
            policy(False)
            time.sleep(2)
            kubectl('-n', 'demo-clase', 'scale', 'deployment/hola-gitops', '--replicas=2')
            event('Cambio manual: Deployment.spec.replicas=2. Git sigue declarando 3. No se modifico Git.', 'drift')
        elif name == 'enable-heal':
            policy(True)
        elif name == 'drift-with-heal':
            with STATE_LOCK:
                ready = STATE.get('connected') and STATE.get('git', {}).get('replicas') == 3 and STATE.get('cluster', {}).get('target') == 3 and STATE.get('argo', {}).get('selfHeal') is True
            if not ready:
                raise RuntimeError('Esta comprobacion requiere Git=3, Deployment=3 y selfHeal activo.')
            kubectl('-n', 'demo-clase', 'scale', 'deployment/hola-gitops', '--replicas=2')
            event('Nuevo cambio manual a 2 con selfHeal activo. Argo CD volvera a aplicar las 3 replicas de Git.', 'drift')
        elif name == 'reset':
            policy(True)
            publish(2)
        else:
            raise RuntimeError('Accion no permitida.')
    except Exception as error:
        event('No se pudo completar la accion: ' + str(error), 'error')
        with STATE_LOCK:
            STATE['actionError'] = str(error)
    finally:
        with STATE_LOCK:
            STATE['busy'] = False
        ACTION_LOCK.release()


class Handler(BaseHTTPRequestHandler):
    def send(self, code, data, content_type='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            self.send(200, (ROOT / 'web' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/api/state':
            with STATE_LOCK:
                self.send(200, {**STATE, 'events': EVENTS[-12:]})
        elif self.path == '/api/evidence':
            with STATE_LOCK:
                self.send(200, {**STATE, 'events': list(EVENTS)})
        elif self.path == '/favicon.ico':
            self.send(204, b'')
        else:
            self.send(404, {'error': 'No encontrado'})

    def do_POST(self):
        # Solo acciones predefinidas, con encabezado no simple y sin CORS.
        if self.headers.get('X-Demo-Action') != '1' or self.headers.get('Origin', 'http://127.0.0.1:14590') not in ('http://127.0.0.1:14590', 'http://localhost:14590'):
            self.send(403, {'error': 'Origen no permitido'})
            return
        if self.path != '/api/action':
            self.send(404, {'error': 'No encontrado'})
            return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size < 1024:
                raise ValueError('Peticion no valida')
            action = json.loads(self.rfile.read(size))['action']
            if action not in ('publish-three', 'drift-without-heal', 'enable-heal', 'drift-with-heal', 'reset'):
                raise ValueError('Accion desconocida')
        except (ValueError, KeyError):
            self.send(400, {'error': 'Peticion no valida'})
            return
        if not ACTION_LOCK.acquire(blocking=False):
            self.send(409, {'error': 'Espera a que termine la accion actual'})
            return
        with STATE_LOCK:
            STATE.update(busy=True, action=action, actionError=None)
        threading.Thread(target=do_action, args=(action,), daemon=True).start()
        self.send(202, {'accepted': True, 'action': action})

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    LOCAL.mkdir(exist_ok=True)
    threading.Thread(target=poll, daemon=True).start()
    print('Panel: http://127.0.0.1:14590', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 14590), Handler).serve_forever()
