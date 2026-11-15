# =============================================================================
# Equipo 6 - Genera tráfico contra el servicio de notificaciones para la demo:
# CRUD completo + un 404 + un 422 (+ /health y /metrics).
#
# Requiere el port-forward abierto:
#   kubectl -n proyecto-final port-forward svc/notificaciones 8001:80
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File kubernetes\notifications\trafico_notificaciones.ps1 [-Rondas 10]
# =============================================================================
param([int]$Rondas = 1, [string]$Api = "http://localhost:8001")

function Llamar($metodo, $ruta, $body) {
    $curlArgs = @("-s", "-o", "NUL", "-w", "%{http_code}", "-X", $metodo, "$Api$ruta")
    $tmp = $null
    if ($body) {
        $tmp = New-TemporaryFile
        [IO.File]::WriteAllText($tmp, $body)
        $curlArgs += @("-H", "Content-Type: application/json", "--data-binary", "@$tmp")
    }
    $code = & curl.exe @curlArgs
    if ($tmp) { Remove-Item $tmp }
    Write-Host ("{0,-6} {1,-45} -> {2}" -f $metodo, $ruta, $code)
}

for ($r = 1; $r -le $Rondas; $r++) {
    $codigo = "DEMO-" + (Get-Random -Maximum 999999)
    $nueva = @{
        codigo = $codigo; tipo = "notificacion_general"; canal = "email"
        destinatario_id = "usuario-demo"; titulo = "Prueba demo"; mensaje = "Hola desde la demo"
    } | ConvertTo-Json -Compress

    $creada = Invoke-RestMethod -Method Post -Uri "$Api/notificaciones" -ContentType "application/json" -Body $nueva
    Write-Host ("POST   /notificaciones                               -> 201 (id {0})" -f $creada.id)
    $id = $creada.id

    Llamar GET    "/notificaciones"
    Llamar GET    "/notificaciones/$id"
    Llamar PUT    "/notificaciones/$id" '{"titulo":"Prueba demo (editada)","estado":"enviada"}'
    Llamar DELETE "/notificaciones/$id"
    Llamar GET    "/notificaciones/000000000000000000000000"          # 404: ID inexistente
    Llamar POST   "/notificaciones" '{"codigo":"x","tipo":"no_existe"}'  # 422: payload inválido
    if ($Rondas -gt 1) { Start-Sleep -Milliseconds 500 }
}
Llamar GET "/health"
Llamar GET "/metrics"
