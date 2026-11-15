# =============================================================================
# Equipo 6 - Notificaciones: levanta TODO el Proyecto 2 en el cluster Kind local.
#
# Uso (PowerShell, desde cualquier carpeta):
#   powershell -ExecutionPolicy Bypass -File kubernetes\notifications\levantar_notificaciones.ps1
#
# Qué hace:
#   1. Crea el cluster Kind "web3" y el namespace proyecto-final si no existen.
#   2. Construye la imagen del servicio con el código local y la carga en Kind.
#   3. Aplica Mongo + ConfigMap/Secret/Deployment/Services de notificaciones.
#   4. Aplica Prometheus + Grafana (monitoring_tools.yaml) y Loki + Alloy
#      (logging.yaml) en el namespace default.
#   5. Importa el dashboard de Grafana (grafana/notificaciones-dashboard.json).
# =============================================================================
$ErrorActionPreference = "Stop"

$Cluster  = "web3"
$NS       = "proyecto-final"
$Image    = "ghcr.io/sergiomdza/notificaciones:latest"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$K8s      = Join-Path $RepoRoot "kubernetes"
$GrafanaUser = "grafana_admin"
$GrafanaPass = "web3"

function Paso($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Run {
    # Ejecuta un comando externo y se detiene si falla.
    $exe = $args[0]; $rest = $args[1..($args.Length - 1)]
    & $exe @rest
    if ($LASTEXITCODE -ne 0) { throw "Falló: $($args -join ' ')" }
}

Paso "Verificando herramientas"
foreach ($cmd in "docker", "kind", "kubectl") {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Falta '$cmd' en el PATH" }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker no está corriendo. Abre Docker Desktop y vuelve a intentar." }

Paso "Cluster Kind '$Cluster'"
$clusters = @(kind get clusters 2>$null)
if ($clusters -notcontains $Cluster) { Run kind create cluster --name $Cluster }
Run kubectl config use-context "kind-$Cluster"
kubectl get namespace $NS *> $null
if ($LASTEXITCODE -ne 0) { Run kubectl create namespace $NS }

Paso "Construyendo imagen $Image con el código local"
Run docker build -t $Image (Join-Path $RepoRoot "backend\notifications")
Run kind load docker-image $Image --name $Cluster

Paso "MongoDB"
Run kubectl apply -f (Join-Path $K8s "mongo_statefulset.yaml")

Paso "Servicio de notificaciones"
# Si existe un Deployment viejo con otro label en el selector (inmutable), se recrea.
$selector = kubectl -n $NS get deployment notificaciones -o jsonpath="{.spec.selector.matchLabels.app}" 2>$null
if ($LASTEXITCODE -eq 0 -and $selector -and $selector -ne "notifications-backend") {
    Run kubectl -n $NS delete deployment notificaciones
}
Run kubectl apply -f (Join-Path $K8s "notifications\configmap.yaml") -f (Join-Path $K8s "notifications\secret.yaml") -f (Join-Path $K8s "notifications\service.yaml") -f (Join-Path $K8s "notifications\deployment.yaml")
# La imagen conserva el mismo tag: se reinicia para que tome la recién cargada.
Run kubectl -n $NS rollout restart deployment notificaciones
Run kubectl -n $NS rollout status statefulset mongo --timeout=300s
Run kubectl -n $NS rollout status deployment notificaciones --timeout=300s

Paso "Prometheus + Grafana + Loki + Alloy (namespace default)"
Run kubectl apply -n default -f (Join-Path $K8s "monitoring_tools.yaml")
Run kubectl apply -f (Join-Path $K8s "logging.yaml")
# Reinicio para que tomen los ConfigMaps nuevos.
Run kubectl -n default rollout restart deployment prometheus grafana alloy
foreach ($d in "prometheus", "grafana", "loki", "alloy") {
    Run kubectl -n default rollout status deployment $d --timeout=300s
}

Paso "Importando dashboard en Grafana"
$pf = Start-Process kubectl -ArgumentList "-n default port-forward svc/grafana-service 13000:3000" -WindowStyle Hidden -PassThru
try {
    $ok = $false
    for ($i = 0; $i -lt 40 -and -not $ok; $i++) {
        try { Invoke-RestMethod "http://localhost:13000/api/health" | Out-Null; $ok = $true } catch { Start-Sleep 1 }
    }
    if (-not $ok) { throw "Grafana no respondió en el port-forward" }
    $dash = Get-Content (Join-Path $K8s "notifications\grafana\notificaciones-dashboard.json") -Raw -Encoding UTF8
    $body = "{`"dashboard`": $dash, `"overwrite`": true}"
    $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GrafanaUser}:${GrafanaPass}"))
    $resp = Invoke-RestMethod -Method Post -Uri "http://localhost:13000/api/dashboards/db" `
        -Headers @{ Authorization = "Basic $auth" } -ContentType "application/json; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($body))
    Write-Host "Dashboard: $($resp.status) -> $($resp.url)"
} finally {
    Stop-Process -Id $pf.Id -ErrorAction SilentlyContinue
}

Paso "Listo"
kubectl get pods -n $NS -o wide
kubectl get pods -n default
@"

Abre cada uno en una terminal aparte (o con el botón de port-forward de OpenLens):
  kubectl -n proyecto-final port-forward svc/notificaciones 8001:80
      -> http://localhost:8001/docs   (Swagger)   http://localhost:8001/metrics
  kubectl -n default port-forward svc/prometheus-service 9090:9090
      -> http://localhost:9090/targets   (job "notificaciones": 2 targets UP)
  kubectl -n default port-forward svc/grafana-service 3000:3000
      -> http://localhost:3000/d/notificaciones   (usuario $GrafanaUser / $GrafanaPass)
      -> Explore -> Loki:  {app="notifications-backend"}
"@
