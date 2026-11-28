// Código compartido por smoke.js y load.js: el "usuario virtual" (VU) de K6
// ejecuta este flujo CRUD contra el servicio de notificaciones.
import http from 'k6/http';
import { check, group, sleep } from 'k6';

// Dentro del cluster se usa el DNS del Service; se puede cambiar con la variable BASE_URL.
export const BASE_URL =
  __ENV.BASE_URL || 'http://notificaciones.proyecto-final.svc.cluster.local';

const JSON_HEADERS = { 'Content-Type': 'application/json' };

// Se etiqueta cada request con un "name" fijo. Sin esto, K6 crearía una serie
// distinta por cada /notificaciones/<id> y las métricas por endpoint serían inútiles.
function params(name) {
  return { headers: JSON_HEADERS, tags: { name } };
}

function cuerpoNuevo() {
  return JSON.stringify({
    // El código debe ser único (Mongo tiene un índice único): VU + iteración + timestamp.
    codigo: `K6-${__VU}-${__ITER}-${Date.now()}`,
    tipo: 'notificacion_general',
    canal: 'email',
    destinatario_id: `usuario-k6-${__VU}`,
    titulo: 'Prueba de carga K6',
    mensaje: 'Notificación generada por K6',
  });
}

// Una iteración completa: health -> crear -> listar -> leer -> editar -> borrar.
// `pausa` simula el tiempo que tarda una persona entre acciones (think time).
export function flujoCrud(pausa = 1) {
  group('health', () => {
    const res = http.get(`${BASE_URL}/health`, params('GET /health'));
    check(res, { 'health 200': (r) => r.status === 200 });
  });

  let id;
  group('crear', () => {
    const res = http.post(
      `${BASE_URL}/notificaciones`,
      cuerpoNuevo(),
      params('POST /notificaciones'),
    );
    const ok = check(res, { 'crear 201': (r) => r.status === 201 });
    if (ok) id = res.json('id');
  });

  // Si no se pudo crear no tiene sentido seguir con el resto de la iteración.
  if (!id) return;

  group('consultar', () => {
    const lista = http.get(
      `${BASE_URL}/notificaciones?limit=20`,
      params('GET /notificaciones'),
    );
    check(lista, { 'listar 200': (r) => r.status === 200 });

    const una = http.get(
      `${BASE_URL}/notificaciones/${id}`,
      params('GET /notificaciones/{id}'),
    );
    check(una, { 'leer 200': (r) => r.status === 200 });
  });

  sleep(pausa);

  group('modificar y limpiar', () => {
    const put = http.put(
      `${BASE_URL}/notificaciones/${id}`,
      JSON.stringify({ titulo: 'Prueba K6 (editada)', estado: 'enviada' }),
      params('PUT /notificaciones/{id}'),
    );
    check(put, { 'editar 200': (r) => r.status === 200 });

    const del = http.del(
      `${BASE_URL}/notificaciones/${id}`,
      null,
      params('DELETE /notificaciones/{id}'),
    );
    check(del, { 'borrar 204': (r) => r.status === 204 });
  });
}
