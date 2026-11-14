# Comandos equivalentes al panel

Ejecutar desde la carpeta del repositorio en PowerShell. El kubeconfig explícito
evita dirigir los comandos al clúster de otra práctica.

```powershell
$labKube = Join-Path (Get-Location) '.local\kubeconfig'
kubectl --kubeconfig $labKube --context kind-gitops-clase -n demo-clase get deployment,pods
kubectl --kubeconfig $labKube --context kind-gitops-clase -n argocd get application hola-gitops
```

## Cambio aprobado desde Git

Editar `k8s/deployment.yaml`: cambiar `replicas: 2` a `replicas: 3`.

```powershell
git add k8s/deployment.yaml
git commit -m 'demo: declarar 3 replicas en Git'
git push origin main
```

Esperar a que Argo CD sincronice. No ejecutar `kubectl apply` del Deployment.

## Observar un desvío sin selfHeal

```powershell
kubectl --kubeconfig $labKube --context kind-gitops-clase -n argocd patch application hola-gitops --type merge -p '{"spec":{"syncPolicy":{"automated":{"enabled":true,"selfHeal":false}}}}'
kubectl --kubeconfig $labKube --context kind-gitops-clase -n demo-clase scale deployment/hola-gitops --replicas=2
kubectl --kubeconfig $labKube --context kind-gitops-clase -n argocd get application hola-gitops
```

Esperar `OutOfSync`. Git conserva las tres réplicas.

## Activar la reparación

```powershell
kubectl --kubeconfig $labKube --context kind-gitops-clase -n argocd patch application hola-gitops --type merge -p '{"spec":{"syncPolicy":{"automated":{"enabled":true,"selfHeal":true}}}}'
kubectl --kubeconfig $labKube --context kind-gitops-clase -n demo-clase get deployment,pods --watch
```

Salir del seguimiento con Ctrl+C. Volverán tres réplicas.

La Application es el objeto de control usado por el presentador durante esta prueba;
los recursos de la aplicación que reconcilia Argo CD están en `k8s/`.
