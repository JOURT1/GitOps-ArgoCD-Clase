"""Create this educational repository using the user's existing Git credential helper.
No credential is printed, stored in this project, or put in a command argument.
"""
import json
import os
import subprocess
import urllib.error
import urllib.request


def main():
    result = subprocess.run(
        ['git', '-c', 'credential.interactive=false', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\n\n', text=True,
        capture_output=True, timeout=30,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'},
        check=True,
    )
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    token = fields.get('password')
    if not token:
        raise RuntimeError('Git no tiene una credencial de GitHub disponible.')
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'User-Agent': 'GitOps-Classroom-Demo'}
    request = urllib.request.Request('https://api.github.com/user', headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        user = json.load(response)['login']
    if user.lower() != 'jourt1':
        raise RuntimeError('La credencial no corresponde a JOURT1; no se creo ningun repositorio.')
    url = 'https://api.github.com/repos/JOURT1/GitOps-ArgoCD-Clase'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            existing = json.load(response)
        print(json.dumps({'repository': existing['html_url'], 'created': False}))
        return
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    body = {'name': 'GitOps-ArgoCD-Clase', 'private': False, 'auto_init': False,
            'description': 'Laboratorio de clase: Git como fuente de verdad, Argo CD y selfHeal en Kubernetes local.'}
    request = urllib.request.Request('https://api.github.com/user/repos', headers={**headers, 'Content-Type': 'application/json'},
                                     data=json.dumps(body).encode(), method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        created = json.load(response)
    print(json.dumps({'repository': created['html_url'], 'created': True}))


if __name__ == '__main__':
    main()
