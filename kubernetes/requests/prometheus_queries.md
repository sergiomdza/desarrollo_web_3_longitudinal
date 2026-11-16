
# Consultas Prometheus - Equipo 4

## 1. Disponibilidad del microservicio

```promql
up{job="solicitudes",app="backend-requests"}
```

Resultado esperado: 1 (UP).

## 2. Total acumulado de solicitudes HTTP

```promql
sum by (method, handler) (
  http_requests_total{app="backend-requests"}
)
```

## 3. Solicitudes por segundo

```promql
sum by (method, handler) (
  rate(http_requests_total{app="backend-requests"}[5m])
)
```

## 4. Solicitudes por código HTTP

```promql
sum by (status) (
  increase(http_requests_total{app="backend-requests"}[5m])
)
```

## 5. Latencia promedio en segundos

```promql
sum by (method, handler) (
  rate(http_request_duration_seconds_sum{
    app="backend-requests"
  }[5m])
)
/
sum by (method, handler) (
  rate(http_request_duration_seconds_count{
    app="backend-requests"
  }[5m])
)
```

## 6. Percentil 95 de latencia

```promql
histogram_quantile(
  0.95,
  sum by (le, handler) (
    rate(http_request_duration_seconds_bucket{
      app="backend-requests"
    }[5m])
  )
)
```

## 7. Tamaño promedio de respuestas

```promql
sum(
  rate(http_response_size_bytes_sum{
    app="backend-requests"
  }[5m])
)
/
sum(
  rate(http_response_size_bytes_count{
    app="backend-requests"
  }[5m])
)
```
