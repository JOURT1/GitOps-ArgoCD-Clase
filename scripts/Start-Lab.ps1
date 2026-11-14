param([switch]$NoPanel)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoRoot
$localDir = Join-Path $repoRoot '.local'
$toolsDir = Join-Path $repoRoot '.tools'
New-Item -ItemType Directory -Path $localDir,$toolsDir -Force | Out-Null
$kubeConfig = Join-Path $localDir 'kubeconfig'
$kindPath = Join-Path $toolsDir 'kind.exe'
if (-not (Test-Path -LiteralPath $kindPath)) {
    $existing = Join-Path (Split-Path $repoRoot -Parent) 'SARSEG-Kubernetes-P2\.tools\kind.exe'
    if (Test-Path -LiteralPath $existing) { Copy-Item -LiteralPath $existing -Destination $kindPath }
    else {
        $base = 'https://github.com/kubernetes-sigs/kind/releases/download/v0.27.0'
        Invoke-WebRequest "$base/kind-windows-amd64" -OutFile $kindPath
        $hash = (Invoke-WebRequest "$base/kind-windows-amd64.sha256sum").Content
        if ($hash -is [byte[]]) { $hash = [Text.Encoding]::UTF8.GetString($hash) }
        if ((Get-FileHash -LiteralPath $kindPath -Algorithm SHA256).Hash.ToLower() -ne ($hash.Trim() -split '\s+')[0]) { throw 'El hash de kind no coincide con el publicado.' }
    }
}
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Inicia Docker Desktop con contenedores Linux y repite el comando.' }
$clusters = @(& $kindPath get clusters)
if ($clusters -notcontains 'gitops-clase') {
    & $kindPath create cluster --config (Join-Path $repoRoot 'cluster\kind.yaml') --kubeconfig $kubeConfig --wait 180s
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el cluster de la demostracion.' }
} else {
    & $kindPath export kubeconfig --name gitops-clase --kubeconfig $kubeConfig
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo recuperar el kubeconfig del laboratorio.' }
}
function Invoke-LabKubectl {
    & kubectl --kubeconfig $kubeConfig --context kind-gitops-clase @args
    if ($LASTEXITCODE -ne 0) { throw "kubectl fallo: $args" }
}
foreach ($ns in @('argocd','demo-clase')) {
    & kubectl --kubeconfig $kubeConfig --context kind-gitops-clase get namespace $ns *> $null
    if ($LASTEXITCODE -ne 0) { Invoke-LabKubectl create namespace $ns }
}
$argoVersion = 'v3.4.13'
$installFile = Join-Path $localDir "argocd-$argoVersion-install.yaml"
if (-not (Test-Path -LiteralPath $installFile)) {
    Invoke-WebRequest "https://raw.githubusercontent.com/argoproj/argo-cd/$argoVersion/manifests/install.yaml" -OutFile $installFile
}
Invoke-LabKubectl apply --server-side --force-conflicts -n argocd -f $installFile
# Configuracion exclusiva de este cluster local. Argo CD se expone en loopback.
$settings = @'
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-cm
    app.kubernetes.io/part-of: argocd
data:
  users.anonymous.enabled: "true"
  timeout.reconciliation: "10s"
  timeout.reconciliation.jitter: "0s"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-rbac-cm
    app.kubernetes.io/part-of: argocd
data:
  policy.default: role:readonly
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-cmd-params-cm
    app.kubernetes.io/part-of: argocd
data:
  server.insecure: "true"
  controller.self.heal.timeout.seconds: "5"
'@
$settings | & kubectl --kubeconfig $kubeConfig --context kind-gitops-clase apply --server-side --field-manager=gitops-clase-settings --force-conflicts -f -
if ($LASTEXITCODE -ne 0) { throw 'No se pudo configurar Argo CD.' }
Invoke-LabKubectl -n argocd patch service argocd-server --type merge -p '{"spec":{"type":"NodePort","ports":[{"name":"http","port":80,"protocol":"TCP","targetPort":8080,"nodePort":30080}]}}'
# Reiniciar solo estos dos controladores hace que lean los parametros del laboratorio.
Invoke-LabKubectl -n argocd rollout restart deployment/argocd-server deployment/argocd-repo-server
Invoke-LabKubectl -n argocd rollout restart statefulset/argocd-application-controller
Invoke-LabKubectl -n argocd rollout status deployment/argocd-server --timeout=300s
Invoke-LabKubectl -n argocd rollout status deployment/argocd-repo-server --timeout=300s
Invoke-LabKubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
Invoke-LabKubectl apply -f (Join-Path $repoRoot 'argocd\project.yaml') -f (Join-Path $repoRoot 'argocd\application.yaml')
Write-Host 'Esperando el primer despliegue desde Git...'
$deadline = (Get-Date).AddMinutes(5)
do {
    $app = (& kubectl --kubeconfig $kubeConfig --context kind-gitops-clase -n argocd get application hola-gitops -o json | ConvertFrom-Json)
    if ($app.status.sync.status -eq 'Synced' -and $app.status.health.status -eq 'Healthy') { break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)
if ($app.status.sync.status -ne 'Synced' -or $app.status.health.status -ne 'Healthy') { throw 'La aplicacion no llego a Synced / Healthy. Consulta kubectl get application hola-gitops -n argocd con el kubeconfig local.' }
Invoke-LabKubectl -n demo-clase get 'deployments,pods,services'
$response = Invoke-WebRequest 'http://127.0.0.1:14500/'
if ($response.StatusCode -ne 200) { throw 'La pagina de demostracion no responde.' }
if (-not $NoPanel) {
    $pythonPath = (Get-Command python).Source
    $listener = Get-NetTCPConnection -State Listen -LocalPort 14590 -ErrorAction SilentlyContinue
    if (-not $listener) {
        $process = Start-Process -FilePath $pythonPath -ArgumentList @((Join-Path $PSScriptRoot 'panel.py')) -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localDir 'panel.stdout.log') -RedirectStandardError (Join-Path $localDir 'panel.stderr.log') -PassThru
        $process.Id | Set-Content -LiteralPath (Join-Path $localDir 'panel.pid')
    }
}
Write-Host 'Panel de la actividad: http://127.0.0.1:14590'
Write-Host 'Interfaz de Argo CD: http://127.0.0.1:14580'
Write-Host 'Pagina desplegada: http://127.0.0.1:14500'
