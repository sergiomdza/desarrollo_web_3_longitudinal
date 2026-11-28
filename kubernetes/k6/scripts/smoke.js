// SMOKE TEST: "¿el servicio funciona en lo más básico?"
// Carga mínima (1 usuario virtual) durante poco tiempo. No busca estresar nada:
// si esta prueba falla, no tiene sentido lanzar la de carga.
import { flujoCrud } from './common.js';

export const options = {
  vus: 1,
  duration: '30s',

  // Thresholds: criterios de éxito. Si alguno no se cumple, K6 termina con
  // código distinto de 0 y el Job de Kubernetes queda en estado Failed.
  thresholds: {
    http_req_failed: ['rate<0.01'], // menos de 1% de requests con error
    http_req_duration: ['p(95)<800'], // el 95% responde en menos de 800 ms
    checks: ['rate>0.99'], // más de 99% de los check() deben pasar
  },
};

export default function () {
  flujoCrud(1);
}
