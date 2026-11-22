# Decisiones técnicas · paso 4 (tablero en vivo, reloj real, worker, Cloudflare)

Rama `feature/tablero-vivo`.

## 1. Cómo viaja un evento

```
API o worker ──(misma transacción del cambio)──► pg_notify('vela_events', {...})
PostgreSQL ──(solo al hacer COMMIT)──► conexión LISTEN de la API ──► Hub ──► /ws/board (wss://)
navegador ──► vuelve a leer GET /api/board (con seguridad por fila y alcance por rol)
```

- **El aviso sale solo si el cambio se guardó.** `pg_notify` dentro de una transacción se entrega al hacer
  COMMIT; si la transacción se deshace, no hay evento (prueba `test_rolled_back_change_sends_no_event`).
- **El evento no lleva datos personales**: tipo, institución e identificadores. El tablero vuelve a leer
  `/api/board`, así que el WebSocket no es una segunda puerta a los datos: la seguridad sigue siendo la de
  la API (RLS + rol).
- **Filtro por institución** en el Hub: un coordinador solo recibe eventos de su institución; Dirección
  (`owner`) los recibe todos. Prueba: se publica uno de INS-B y luego uno de INS-A; el primero que recibe
  INS-A es el suyo.
- Eventos: `request.created`, `request.updated` (rechazada, cerrada, sin atender), `assignment.proposed`,
  `assignment.approved` (automática o aprobada), `visit.arrived`, `visit.finished`, `alert.created`.
  `request.updated` se agregó para que el tablero también se entere de esos cambios de estado.
- Medido por el túnel de Cloudflare: **≈ 0.05 s** del COMMIT al mensaje en el WebSocket (criterio: < 2 s).

## 2. Seguridad del WebSocket

- Se autentica con **la misma cookie de sesión** (`httpOnly`), revisada en la base al conectar y cada 60 s.
  Solo entran coordinación y dirección. Cierres: `4401` sin sesión, `4403` rol sin tablero u origen ajeno.
- **Revisión de `Origin`** (evita que otra página use la cookie del usuario para abrir el socket): se compara
  solo el **host**, no el esquema, porque dentro de Docker todo llega como http.
- `ping` cada 25 s: Cloudflare cierra los WebSocket inactivos a los ~100 s.

## 3. Reconexión de LISTEN (PostgreSQL reiniciado)

`listen_forever()` mantiene una conexión `LISTEN`; cada 15 s hace `SELECT 1` y usa *keepalives* TCP. Si la
conexión muere, reintenta cada 2 s y, al volver, envía `board.resync` para que cada tablero recargue (pudo
perder eventos mientras tanto). `GET /api/health` informa `"realtime": "ok"` o `"reconnecting"`.

- **Prueba automática**: `test_listener_reconnects_after_its_connection_dies` termina la conexión LISTEN con
  `pg_terminate_backend` y comprueba que vuelve a escuchar y entrega eventos.
- **Revisión manual** (hecha el 21 nov 2026): `docker compose restart db` → `/api/health` pasó a
  `reconnecting` y en ~2 s volvió a `ok`; en el log: "LISTEN reconnected; asking clients to resync".
- En el navegador, si el socket se cae: "Reconectando…", reintento cada 3 s y recarga completa al volver.

## 4. Cloudflare: https afuera, http adentro

cloudflared habla **http** con Caddy. Si la API mirara solo su propio esquema, pensaría que todo es http y
no marcaría la cookie como `Secure`. Dos mecanismos (ambos comprobados con un túnel real el 21 nov 2026):

1. `Cf-Visitor: {"scheme":"https"}`, que agrega Cloudflare y llega intacta.
2. `X-Forwarded-Proto`: Caddy la **reemplaza** por defecto; con `trusted_proxies static private_ranges` la
   respeta cuando viene de una dirección privada (cloudflared en la laptop).

| Comprobación | Resultado |
|---|---|
| Login por `https://….trycloudflare.com` | cookie con `Secure` |
| Login local por `http://localhost:8080` | cookie sin `Secure` (si no, el navegador no la guardaría) |
| Local con `X-Forwarded-Proto: https` (sin `Cf-Visitor`) | `Secure` → Caddy confía en la red privada |
| WebSocket `wss://` con `Origin` del túnel | acepta; 5 eventos en 0.04–0.06 s |
| WebSocket `wss://` con `Origin: https://evil.example` | cierre 4403 |
| Evento de INS-B y luego de INS-A al coordinador de INS-A | recibe solo el de INS-A |

Ya no hace falta copiar la URL del túnel a `PUBLIC_BASE_URL`. Ojo: `up -d` no recarga el Caddyfile
(está montado); después de cambiarlo, `docker compose restart proxy`.

## 5. Reloj real

`GET /api/time` devuelve la hora del servidor. La interfaz calcula la diferencia con el reloj del dispositivo
(a la mitad del viaje de ida y vuelta), al cargar y cada 5 min, y avanza cada segundo. Siempre muestra la hora
de la Ciudad de México (`Intl`, `America/Mexico_City`), aunque el dispositivo esté en otra zona.

## 6. Solicitudes de los planes de cuidado (movimiento real para la demo)

- Cada plan activo tiene una visita en un día con probabilidad `times_per_week / 7` (máximo 2 por semana
  en la semilla). El sorteo y la hora salen de un **hash** de (plan, fecha): son deterministas, iguales
  aunque el worker se reinicie, y en un mes coinciden con la frecuencia del plan.
- Horario de visita (*supuesto*): 8–18 h en instituciones de día y 7–21 h en las de 24 h, en bloques de 15 min.
- Cada minuto el worker crea las visitas cuya hora de publicación (visita − 2 h) ya llegó y que faltan al
  menos 15 min. Pasan por la misma validación y el mismo despachador que cualquier solicitud.
- La migración 0003 agrega `care_plan_id` y `plan_date` con un índice único: nunca se duplica una visita.
- Volumen esperado: ≈ 91 solicitudes al día en total (INS-A ≈ 32, de ellas ≈ 10 de prioridad alta),
  parecido a las ~100 diarias del historial.
- `verify_db.py` ahora revisa **exactamente** las filas de la semilla (por su rango de claves) e informa
  aparte las creadas en operación, porque con el worker esas tablas crecen.

## 7. Mapa

MapLibre con los estilos de OpenFreeMap (sin llave, © OpenStreetMap). Si no hay internet, los marcadores se
dibujan sobre un fondo liso. Cada marcador tiene ícono **y** palabra, y la lista debajo del mapa repite la
información. MapLibre se carga solo al abrir el tablero (pesa ~1 MB); el celular del familiar no lo descarga.

## 8. Fechas vivas (`scripts/rebase_dates.py`)

Mueve el historial por **semanas completas**, para conservar el día de la semana, y lo deja terminando entre
0 y 6 días antes de ayer. No toca `audit_log` (la bitácora es cronología real), las alertas ni las visitas
de hoy o futuras. Las filas con reglas de unicidad o de no traslape se mueven en dos pasos (primero +1000
años, luego a su lugar), para no chocar entre sí a mitad de la actualización. Detalle en la guía, sección
"Día de la defensa".
