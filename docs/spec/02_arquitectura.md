# 02 · Arquitectura e infraestructura

```
 Internet ──► Cloudflare (https://<aleatorio>.trycloudflare.com)
                 │  túnel saliente, no se abren puertos del router
                 ▼
 Laptop Ryzen ── cloudflared ──► localhost:8080  Caddy (proxy)
                                     ├── /        → web   (React compilado)
                                     ├── /api/*   → api   (FastAPI :8000)
                                     └── /ws/*    → api   (WebSocket)
                 api ──► db (PostgreSQL 16 + PostGIS)      worker ──► db
                 api ──► Ollama en Windows (host.docker.internal:11434)
                 api ──► faster-whisper (dentro del contenedor, CPU)
```

## Servicios (Docker Compose)
| Servicio | Imagen / base | Función |
|---|---|---|
| `db` | `postgis/postgis:16-3.4` | Datos; carga semillas la primera vez (`infra/db-init.sh`) |
| `api` | `python:3.12-slim` | FastAPI: REST + WebSocket, autenticación, reglas de negocio, voz |
| `worker` | misma imagen que `api` | Ciclo cada minuto: calidad del aire, contingencia, cola, riesgo, solicitudes del plan de cuidado |
| `web` | `node:22` (build) | Compila el frontend; Caddy sirve los archivos |
| `proxy` | `caddy:2` | Un solo puerto público (8080) |

Fuera de Docker: **Ollama** (Windows, backend Vulkan para la GPU integrada Radeon) y **cloudflared**.

## Tiempo real
- El reloj de la interfaz se sincroniza con `GET /api/time` y avanza localmente cada segundo.
- `worker` publica eventos en PostgreSQL `LISTEN/NOTIFY`; `api` los reenvía por WebSocket
  (`/ws/board?institution=…`). Eventos: `request.created`, `assignment.proposed`, `assignment.approved`,
  `visit.arrived`, `visit.finished`, `alert.created`, `contingency.changed`.
- Si el WebSocket se cae, la interfaz reintenta cada 3 s y muestra "Reconectando…".

## Seguridad
- Sesión con JWT en cookie `httpOnly`, `Secure`, `SameSite=Lax`; contraseñas bcrypt.
- Cada petición abre transacción con `SET LOCAL app.institution_id`. La API usa el rol `vela_api`,
  sujeto a seguridad a nivel de fila (sin valor → 0 filas).
- Limitar intentos de inicio de sesión (5 por minuto por IP).
- La base de datos solo escucha en `127.0.0.1`.

## Límites del túnel rápido
URL aleatoria que cambia al reiniciar, máximo 200 peticiones simultáneas, sin SSE y sin garantía de
disponibilidad (es para pruebas). Para la defensa: dejar el túnel corriendo desde antes, tener el enlace
en un código QR y, como respaldo, la demo en `localhost:8080`. Opción estable: túnel con nombre y dominio propio.

## Rendimiento esperado en la laptop
- PostgreSQL y FastAPI: holgados para 5 instituciones y ~30 usuarios.
- Whisper `small` int8 en CPU: unos segundos por nota de voz de 20 s (medirlo y documentarlo).
- LLM 7–8 B cuantizado: generación del reporte en decenas de segundos; por eso la pantalla 911 no espera al LLM.
