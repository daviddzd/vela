# Plan B y problemas comunes {#cap-planb}

## En una frase

!!! frase "En una frase"
    **Para cada cosa que puede fallar el día de la defensa hay un plan B que se puede aplicar en menos de un minuto, y casi
    todo sigue funcionando sin internet porque corre en la laptop.**

## Explicado sin tecnicismos

Un buen piloto revisa antes de despegar qué hará si falla cada instrumento. Esta tabla es esa revisión.

## Por qué lo hicimos así

Todo lo crítico corre en la laptop (base, API, voz, modelo de lenguaje). Lo externo (el túnel y las calles del mapa) tiene un
respaldo que no depende de internet.

## Cómo funciona por dentro

### Plan B por falla

| Si falla… | Qué se ve | Plan B |
|---|---|---|
| El internet de la escuela | el QR no abre; el mapa muestra solo alcaldías | seguir en `http://localhost:8080` en el proyector; el mapa de alcaldías funciona sin internet |
| El túnel de Cloudflare | error 502 o 1033 en el enlace | `docker compose ps`; si la app está bien, reabrir el túnel y generar otro QR; si no hay tiempo, `localhost` |
| Ollama (modelo de lenguaje) | «El reporte se está preparando…» por mucho tiempo o «no se pudo generar» | la pantalla 911 y las alertas **no dependen** del modelo; explicar que el médico recibe transcripción y nivel; reabrir Ollama |
| El servicio de voz o el micrófono | «El servicio de voz no responde» o micrófono denegado | escribir el mensaje (mismo flujo: reglas, clasificador, pantalla) |
| El clasificador da ámbar en una frase rutinaria | aviso ámbar | usarlo para explicar los dos niveles y la revisión humana |
| La contingencia no aparece | `/contingencia` sin propuesta | esperar al siguiente minuto del worker; revisar que el escenario esté «Activo» en `/demo` |
| La sesión se cierra sola | «Inicia sesión para continuar» | el reloj de WSL2 se atrasó; la API tolera {{ code.clock_leeway }}; si persiste, `wsl --shutdown` en PowerShell y volver a encender |
| El tablero dice «Reconectando…» | no se actualiza | `curl localhost:8080/api/health` debe decir `"realtime":"ok"`; `docker compose restart api` |
| La base quedó mal tras un ensayo | datos raros | `bash scripts/restore_db.sh backups/<último>.dump` o `python3 scripts/reset_demo.py` |
| Todo lo anterior | — | video grabado de la demostración completa |

### Problemas comunes al preparar

| Síntoma | Solución |
|---|---|
| `docker: command not found` en Ubuntu | Docker Desktop → Settings → Resources → WSL integration → activar Ubuntu |
| La API no alcanza a Ollama | en PowerShell `setx OLLAMA_HOST 0.0.0.0:11434`, reiniciar Ollama y permitir el acceso en el firewall solo para redes privadas |
| `verify_db.py` falla en conteos | `docker compose down -v` y `docker compose up -d` (la carga solo corre con el volumen vacío) — antes, `backup_db.sh` |
| Cambié `infra/Caddyfile` y no hace caso | `docker compose restart proxy` (`up -d` no lo recarga) |
| Todo va lento | cerrar pestañas; usar un modelo más chico en `OLLAMA_MODEL` |
| Las pruebas fallan con «Inicia sesión» | el reloj de WSL2 (ver arriba) |

### Qué revisar 30 minutos antes

```bash
curl -s localhost:8080/api/health       # status ok, db ok, realtime ok
python3 scripts/verify_db.py            # Todo correcto
docker compose ps                       # todo "running" o "healthy"
```

Y en Windows: `ollama ps` (modelo cargado) y la ventana de `cloudflared` abierta.

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Problemas comunes (versión larga) | `docs/00_preparar_laptop_y_github.md`, «Problemas comunes» |
| Mapa sin internet | `frontend/src/components/StreetMap.tsx` (respaldo de alcaldías) |
| Tolerancia del reloj | `backend/app/core/security.py` (`CLOCK_LEEWAY_SECONDS`) |

## Números clave

{{ tabla code.clock_leeway code.ws_retry_s man.reconexion_listen_s code.worker_tick }}

## Limitaciones honestas

- El plan B depende de que la laptop funcione: no hay una segunda laptop configurada.
- El video hay que grabarlo después del último cambio de interfaz.

## Preguntas que te pueden hacer

!!! pregunta "¿Qué pasa si se cae el internet durante la defensa?"
    Seguimos en `localhost:8080`: la base, la API, la voz y el modelo de lenguaje corren en la laptop. Solo se pierden el enlace
    público y las calles del mapa, que cae a un mapa de alcaldías.
