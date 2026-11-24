# 10 · Plan, guion de demo y criterios de aceptación

## Plan día por día (con Claude Code)
| Día | Fecha | Meta (al final del día debe funcionar) |
|---|---|---|
| 1 | vie 21 nov | Laptop lista, repo en GitHub, `docker compose up db`, `verify_db.py` en verde |
| 2 | sáb 22 nov | API: login, roles, seguridad por institución, bitácora; pruebas de aislamiento |
| 3 | dom 23 nov | Solicitudes, asignación automática, cola de aprobaciones; pantallas de cuidador y familia |
| 4 | lun 24 nov | Tablero en vivo con WebSocket, reloj real, worker; Caddy en :8080; primera prueba con Cloudflare |
| 5 | mar 25 nov | Panorama-AM: tableros y mapa |
| 6 | mié 26 nov | SIRAG-D: modelo, 30 réplicas, página de resultados |
| 7 | jue 27 nov | Contingencia en vivo: detección → propuesta → aprobación; panel `/demo` |
| 8 | vie 28 nov | Enlaza Voz: Whisper, reglas, clasificador, reporte con Ollama, pantalla 911; evaluación |
| 9 | sáb 29 nov | Negocio, privacidad, consentimientos; pulir accesibilidad y textos |
| 10 | dom 30 nov | Ensayo completo ×3 con cronómetro; arreglar fallas; respaldo en video |
| 11 | lun 1 dic | Encender todo 1 h antes, abrir túnel, QR con el enlace, defensa |

Regla: si un día se atrasa, se recorta **detalle visual**, no funciones; las funciones se terminan primero.

## Guion de la demo (10 min)
| Min | Quién | Qué se muestra |
|---|---|---|
| 0–1 | Emprendimiento | Problema y Enlaza en una frase; el público abre el enlace del QR |
| 1–3 | SIE | Familiar pide servicio → asignación automática → coordinación aprueba una de prioridad alta → aparece en el tablero en vivo |
| 3–5 | Visualización | Panorama-AM: mapa de riesgo, aire, tráfico |
| 5–7 | Simulación | Panel `/demo`: contingencia en el oriente → el sistema propone → coordinación aprueba; resultados de SIRAG-D (política de Enlaza vs. despacho humano) |
| 7–9 | Cómputo Cognitivo | Nota de voz rutinaria → reporte para el médico; frase de emergencia → pantalla 911 |
| 9–10 | Práctica Profesional + Emprendimiento | Consentimiento y bitácora; punto de equilibrio y cierre |

Preguntas probables (5 min): por qué datos sintéticos, qué pasa si falla el internet, cómo se evita que una
institución vea a otra, qué pasa con una falsa alarma, cuánto cuesta operar, cómo se validó la simulación.

## Criterios de aceptación
| # | Criterio | Cómo se comprueba |
|---|---|---|
| A1 | La semilla carga con los conteos esperados y 0 traslapes | `scripts/verify_db.py` |
| A2 | Sin institución en sesión la API ve 0 filas; un usuario de INS-A no puede leer un paciente de INS-B (403 + registro en bitácora) | prueba pytest |
| A3 | Solicitud baja/media se asigna sola en < 5 s; alta queda pendiente hasta aprobación | prueba pytest + manual |
| A4 | El tablero se actualiza sin recargar en < 2 s, también por el enlace de Cloudflare | manual con dos dispositivos |
| A5 | Sin consentimiento vigente no se puede grabar voz ni ver datos de salud | prueba pytest |
| A6 | 100 % de las frases de emergencia del conjunto de prueba terminan en `emergency` | `voice/eval` |
| A7 | La pantalla 911 aparece en < 3 s después de transcribir, sin esperar al LLM | manual con cronómetro |
| A8 | El reporte del médico no contiene diagnósticos (revisión de 20 reportes) | revisión manual |
| A9 | SIRAG-D corre 4 × 3 × 30 y genera intervalos de confianza | `simulation/experiments` |
| A10 | La contingencia del panel demo genera propuesta y nada cambia sin aprobación | manual |
| A11 | Toda cifra visible tiene fuente o dice "supuesto" | revisión |
| A12 | No hay secretos en el repositorio | `git log -p | grep -i password` solo muestra `.env.example` y la contraseña demo |
| A13 | Contraste AA y modo sencillo funcionando | Lighthouse accesibilidad ≥ 90 |
