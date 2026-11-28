// PRUEBA DE CARGA con stages: "¿cómo se comporta el servicio con tráfico realista
// y creciente?". Los usuarios virtuales (VUs) suben y bajan por etapas:
//
//   VUs
//    30 |            ________
//       |           /        \
//    10 |     _____/          \
//       |    /                 \
//     0 |___/                   \___
//        0   30s  1m30  2m   3m   3m30   (tiempo)
import { flujoCrud } from './common.js';

export const options = {
  stages: [ // Pasos a ejecutar
    { duration: '30s', target: 100 }, // ramp-up: de 0 a 10 VUs
    { duration: '1m', target: 100 }, // carga sostenida con 10 VUs
    { duration: '30s', target: 500 }, // subida a 30 VUs
    { duration: '1m', target: 500 }, // carga sostenida con 30 VUs (pico)
    { duration: '30s', target: 0 }, // ramp-down: baja a 0
  ],

  // Thresholds un poco más relajados que en el smoke, porque hay más concurrencia.
  thresholds: {
    http_req_failed: ['rate<0.02'], // menos de 2% de errores
    http_req_duration: ['p(95)<1000', 'p(99)<2000'], // latencias p95 y p99 (ms)
    checks: ['rate>0.98'],
  },
};

export default function () {
  flujoCrud(1);
}
