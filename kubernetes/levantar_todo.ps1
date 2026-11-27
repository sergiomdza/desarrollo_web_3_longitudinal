# =============================================================================
# Equivalente en PowerShell de levantar_todo.sh (para Windows).
# Levanta los 6 microservicios + MongoDB + Prometheus + Grafana + Loki + Alloy
# en el cluster Kind "web3" (namespace proyecto-final) e importa los dashboards.
#
# Uso (desde cualquier carpeta, en Windows PowerShell 5.1 o PowerShell 7):
#   powershell -ExecutionPolicy Bypass -File kubernetes\levantar_todo.ps1
#   .\kubernetes\levantar_todo.ps1 -Cluster web3 -Timeout 300s
#
# Requiere en el PATH: docker (Docker Desktop corriendo), kind y kubectl.
# No requiere Python ni curl.
# =============================================================================
param(
    [string]$Cluster = $(if ($env:CLUSTER) { $env:CLUSTER } else { 'web3' }),
    [string]$Timeout = $(if ($env:TIMEOUT) { $env:TIMEOUT } else { '300s' })
)

# Los ejecutables nativos escriben a stderr aun sin fallar: se valida con $LASTEXITCODE.
$ErrorActionPreference = 'Continue'

$NS = 'proyecto-final'
$GrafanaUser = 'grafana_admin'
$GrafanaPass = 'web3'
$GrafanaLocalPort = 13000
$K8S = $PSScriptRoot
$Fallos = New-Object System.Collections.ArrayList
$PfProc = $null

function Paso($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Aviso($msg) { Write-Host "!! $msg" -ForegroundColor Yellow }

# Espera un rollout; si falla lo registra y sigue con el resto.
function Esperar($tipo, $nombre) {
    kubectl -n $NS rollout status "$tipo/$nombre" "--timeout=$Timeout"
    if ($LASTEXITCODE -ne 0) { [void]$Fallos.Add("$tipo/$nombre") }
}

# Importa un dashboard en Grafana. $archivo = json, $promUid = uid del datasource Prometheus.
function Importar-Dashboard($archivo, $promUid) {
    $nombre = Split-Path $archivo -Leaf
    $raw = [System.IO.File]::ReadAllText($archivo)
    # El dashboard de requests trae un uid de datasource fijo de otro Grafana.
    $raw = $raw.Replace('PBFA97CFB590B2093', $promUid)
    $body = '{"dashboard":' + $raw + ',"overwrite":true}'
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Method Post `
            -Uri "http://localhost:$GrafanaLocalPort/api/dashboards/db" `
            -Headers $script:AuthHeader -ContentType 'application/json' `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
        $url = ($resp.Content | ConvertFrom-Json).url
        Write-Host "  OK  $nombre -> $url"
    } catch {
        $detalle = if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $_.ErrorDetails.Message } else { $_.Exception.Message }
        Aviso "Fallo $nombre : $detalle"
        [void]$Fallos.Add("dashboard/$nombre")
    }
}

# --- 0. Verificaciones -------------------------------------------------------
Paso 'Verificando herramientas'
foreach ($cmd in 'docker', 'kind', 'kubectl') {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "Falta '$cmd' en el PATH"; exit 1
    }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker no esta corriendo. Abre Docker Desktop y reintenta.'; exit 1
}

# --- 1. Cluster y namespace --------------------------------------------------
Paso "Cluster Kind '$Cluster'"
$existentes = @(kind get clusters 2>$null)
if ($existentes -notcontains $Cluster) {
    kind create cluster --name $Cluster --config "$K8S/products/kind-config.yaml"
    if ($LASTEXITCODE -ne 0) { Write-Host 'No se pudo crear el cluster Kind.'; exit 1 }
} else {
    Write-Host 'Ya existe, se reutiliza.'
}
kubectl config use-context "kind-$Cluster" | Out-Null
kubectl apply -f "$K8S/products/namespace.yaml"

# --- 2. MongoDB (compartido) -------------------------------------------------
Paso 'MongoDB'
kubectl apply -f "$K8S/mongo_statefulset.yaml"
Esperar 'statefulset' 'mongo'

# --- 3. Microservicios -------------------------------------------------------
# No se aplica requests/secret.yaml: redefine "mongo-secret" y pisaria el de
# mongo_statefulset.yaml (el deployment de requests usa las mismas claves de usuario/password).
Paso 'Aplicando manifiestos de los 6 microservicios'
kubectl apply `
    -f "$K8S/products/secret.yaml" `
    -f "$K8S/products/backend_configmap.yaml" `
    -f "$K8S/products/backend_deployment.yaml" `
    -f "$K8S/products/observabilidad/metrics_service.yaml"
kubectl apply -f "$K8S/users/backend_deployment.yaml"
kubectl apply `
    -f "$K8S/requests/backend_configmap.yaml" `
    -f "$K8S/requests/backend_deployment.yaml"
kubectl apply -f "$K8S/reports/backend_deployment.yaml"
kubectl apply `
    -f "$K8S/audits/backend_deployment.yaml" `
    -f "$K8S/audits/metrics_service.yaml"
kubectl apply `
    -f "$K8S/notifications/configmap.yaml" `
    -f "$K8S/notifications/secret.yaml" `
    -f "$K8S/notifications/service.yaml" `
    -f "$K8S/notifications/deployment.yaml"

# Los tags `*-latest` no cambian: al re-ejecutar el script, reiniciar fuerza a
# jalar la ultima imagen publicada por el CI/CD.
kubectl -n $NS rollout restart deployment `
    categorias-ubicaciones-api backend requests-backend reportes-backend audits-api notificaciones

# --- 4. Monitoreo ------------------------------------------------------------
Paso 'Prometheus + Grafana + Loki + Alloy'
kubectl apply -f "$K8S/monitoring_tools.yaml"
kubectl apply -f "$K8S/logging.yaml"
# Reinicio para que tomen los ConfigMaps (Prometheus/Alloy no recargan solos).
kubectl -n $NS rollout restart deployment prometheus grafana alloy

Paso 'Esperando a que todo este listo'
foreach ($d in 'categorias-ubicaciones-api', 'backend', 'requests-backend', 'reportes-backend', 'audits-api',
              'notificaciones', 'prometheus', 'grafana', 'loki', 'alloy') {
    Esperar 'deployment' $d
}

# --- 5. Dashboards de Grafana -------------------------------------------------
Paso 'Importando dashboards en Grafana'
$cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GrafanaUser}:${GrafanaPass}"))
$script:AuthHeader = @{ Authorization = "Basic $cred" }
try {
    $PfProc = Start-Process kubectl -PassThru -WindowStyle Hidden `
        -ArgumentList "-n $NS port-forward svc/grafana-service ${GrafanaLocalPort}:3000"
    $ok = $false
    for ($i = 0; $i -lt 40; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing "http://localhost:$GrafanaLocalPort/api/health" | Out-Null
            $ok = $true; break
        } catch { Start-Sleep -Seconds 1 }
    }
    if ($ok) {
        $ds = Invoke-RestMethod -Headers $script:AuthHeader `
            -Uri "http://localhost:$GrafanaLocalPort/api/datasources/name/Prometheus"
        $promUid = $ds.uid
        Importar-Dashboard "$K8S/products/observabilidad/grafana_dashboard.json"      $promUid
        Importar-Dashboard "$K8S/requests/grafana-dashboard.json"                     $promUid
        Importar-Dashboard "$K8S/audits/grafana/audits-dashboard.json"                $promUid
        Importar-Dashboard "$K8S/notifications/grafana/notificaciones-dashboard.json" $promUid
        Importar-Dashboard "$K8S/k6/grafana/k6-dashboard.json"                        $promUid
    } else {
        Aviso 'Grafana no respondio por el port-forward; dashboards no importados.'
        [void]$Fallos.Add('grafana-port-forward')
    }
} finally {
    if ($PfProc -and -not $PfProc.HasExited) { Stop-Process -Id $PfProc.Id -Force -ErrorAction SilentlyContinue }
}

# --- 6. Resumen --------------------------------------------------------------
Paso 'Estado final'
kubectl get pods -n $NS -o wide
if ($Fallos.Count -gt 0) {
    Aviso ("Con problemas: " + ($Fallos -join ' '))
    Aviso "Revisa con: kubectl -n $NS describe pod <pod>  /  kubectl -n $NS logs deploy/<deployment>"
}

Write-Host @"

Accesos (cada uno en una terminal aparte):
  kubectl -n $NS port-forward svc/grafana-service 3000:3000
      -> http://localhost:3000   ($GrafanaUser / $GrafanaPass)   Explore -> Loki: {app="<servicio>"}
  kubectl -n $NS port-forward svc/prometheus-service 9090:9090
      -> http://localhost:9090/targets   (6 jobs en UP)

  kubectl -n $NS port-forward svc/categorias-ubicaciones-service 8000:8000   # products
  kubectl -n $NS port-forward svc/users-service 8001:8000                    # users
  kubectl -n $NS port-forward svc/requests-service 8002:8000                 # requests
  kubectl -n $NS port-forward svc/reportes-service 8003:8000                 # reports
  kubectl -n $NS port-forward svc/audits-service 8004:8001                   # audits
  kubectl -n $NS port-forward svc/notificaciones 8005:80                     # notifications
"@

if ($Fallos.Count -gt 0) { exit 1 }
