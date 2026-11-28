# =============================================================================
# Equivalente en PowerShell de correr_k6.sh (para Windows).
# Corre una prueba de K6 como Job dentro del cluster Kind y muestra su resultado.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File kubernetes\k6\correr_k6.ps1 smoke   # 1 VU, 30 s
#   powershell -ExecutionPolicy Bypass -File kubernetes\k6\correr_k6.ps1 load    # hasta 30 VUs, ~3.5 min
#
# Requiere el stack levantado (kubernetes\levantar_todo.ps1) y kubectl en el PATH.
# =============================================================================
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('smoke', 'load')]
    [string]$Test
)

$ErrorActionPreference = 'Continue'
# Para que los scripts .js con acentos viajen intactos por la tuberia hacia kubectl.
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

$NS = 'proyecto-final'
$DIR = $PSScriptRoot
$JOB = "k6-$Test"

function Fallar($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

Write-Host '==> Verificando que el servicio a probar este arriba...'
kubectl -n $NS get deployment notificaciones *> $null
if ($LASTEXITCODE -ne 0) {
    Fallar "No existe deployment/notificaciones en $NS. Corre primero kubernetes\levantar_todo.ps1"
}
kubectl -n $NS rollout status deployment/notificaciones --timeout=60s

Write-Host '==> Publicando scripts en el ConfigMap k6-scripts...'
kubectl -n $NS create configmap k6-scripts "--from-file=$DIR/scripts" --dry-run=client -o yaml | kubectl apply -f -
if ($LASTEXITCODE -ne 0) { Fallar 'No se pudo publicar el ConfigMap k6-scripts.' }

Write-Host "==> Creando el Job $JOB..."
kubectl -n $NS delete job $JOB --ignore-not-found --wait=true
kubectl apply -f "$DIR/job_$Test.yaml"
if ($LASTEXITCODE -ne 0) { Fallar "No se pudo crear el Job $JOB." }

Write-Host '==> Esperando a que arranque el pod...'
kubectl -n $NS wait --for=condition=Ready pod -l "job-name=$JOB" --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host '(el pod pudo terminar antes de reportar Ready; se muestran los logs igual)'
}

Write-Host '==> Logs de K6 (Ctrl+C solo deja de mostrarlos; la prueba sigue corriendo):'
kubectl -n $NS logs -f "job/$JOB"

Write-Host '==> Resultado del Job:'
$ok = ''; $ko = ''
for ($i = 0; $i -lt 30; $i++) {
    $ok = "$(kubectl -n $NS get job $JOB -o 'jsonpath={.status.succeeded}')"
    $ko = "$(kubectl -n $NS get job $JOB -o 'jsonpath={.status.failed}')"
    if ($ok -or $ko) { break }
    Start-Sleep -Seconds 1
}

if ($ok) {
    Write-Host "OK  $JOB PASO: se cumplieron todos los thresholds." -ForegroundColor Green
} else {
    Fallar "FALLO $JOB : algun threshold no se cumplio (revisa las lineas con X arriba)."
}

Write-Host @"

Para ver las metricas en Grafana:
  kubectl -n $NS port-forward svc/grafana-service 3000:3000
  -> http://localhost:3000/d/k6-notificaciones   (testid = $Test)
"@
