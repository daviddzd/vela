# Plan B y problemas comunes {#cap-planb}

## En una frase

!!! frase "En una frase"
    **Para cada cosa que puede fallar el día de la defensa hay un plan B que se puede aplicar en menos de un minuto, y casi
    todo sigue funcionando sin internet porque corre en la laptop.**

## Explicado sin tecnicismos

Un buen piloto revisa antes de despegar qué hará si falla cada instrumento. Esta tabla es esa revisión.

## Por qué lo hicimos así

Todo lo crítico corre en la laptop (base, API, voz, modelo de lenguaje). Lo externo (el enlace fijo y las calles del mapa)
tiene respaldo: el túnel rápido y, sin internet, `localhost`.

## Cómo funciona por dentro

### Plan B por falla

| Si falla… | Qué se ve | Plan B |
|---|---|---|
| El internet de la escuela | el QR no abre; el mapa muestra solo alcaldías | seguir en `http://localhost:8080` en el proyector; el mapa de alcaldías funciona sin internet |
| La app tras reiniciar | error 502 en `enlaza.zenthinks.com`, o pantallas sin datos | `bash scripts/autostart.sh` (repara los contenedores que salieron sin archivos) |
| El túnel con nombre | error 1033 en `enlaza.zenthinks.com` (p. ej. al cambiar de wifi a hotspot) | se reconecta solo en menos de un minuto (tareas «Enlaza - túnel»). Si no: **PowerShell como administrador → `Restart-Service cloudflared`** (o `bash scripts/enlaza.sh reconectar`). Si en dos minutos no vuelve a **HEALTHY**: túnel rápido `bash scripts/enlaza.sh rapido` (`--protocol http2`), QR nuevo con `make_qr.py` y proyectarlo; si no hay tiempo, `localhost` |
| Ollama (modelo de lenguaje) | «El reporte se está preparando…» por mucho tiempo o «no se pudo generar» | la pantalla 911 y las alertas **no dependen** del modelo; explicar que el médico recibe transcripción y nivel; reabrir Ollama |
| El servicio de voz o el micrófono | «El servicio de voz no responde» o micrófono denegado | escribir el mensaje (mismo flujo: reglas, clasificador, pantalla) |
| El clasificador da ámbar en una frase rutinaria | aviso ámbar | usarlo para explicar los dos niveles y la revisión humana |
| La contingencia no aparece | `/contingencia` sin propuesta | esperar al siguiente minuto del worker; revisar que el escenario esté «Activo» en `/demo` |
| La sesión se cierra sola | «Inicia sesión para continuar» | el reloj de WSL2 se atrasó (la API tolera {{ code.clock_leeway }}); la tarea «Enlaza - reloj de WSL» lo corrige sola; a mano `bash scripts/enlaza.sh reloj`; si persiste, `wsl --shutdown` en PowerShell |
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
bash scripts/enlaza.sh estado           # túnel CONECTADO y en http2, archivos «bien», dirección pública ok, reloj 0 s
uv run scripts/check_public_url.py      # 12 de 12 por https://enlaza.zenthinks.com
```

Y en Windows: `ollama ps` (modelo cargado).

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Problemas comunes (versión larga) | `docs/00_preparar_laptop_y_github.md`, «Problemas comunes» |
| Mapa sin internet | `frontend/src/components/StreetMap.tsx` (respaldo de alcaldías) |
| Tolerancia del reloj | `backend/app/core/security.py` (`CLOCK_LEEWAY_SECONDS`) |
| Arranque y túnel | `scripts/autostart.sh`, `scripts/enlaza.sh`, `scripts/windows/` |
| Reconexión del túnel | `scripts/windows/configure_tunnel_service.ps1` (http2 y permiso), `tunnel_watchdog.ps1`, `install_tunnel_task.ps1` |

## Números clave

{{ tabla code.clock_leeway code.ws_retry_s man.reconexion_listen_s code.worker_tick }}

## Limitaciones honestas

- El plan B depende de que la laptop funcione: no hay una segunda laptop configurada.
- La reconexión automática solo corre con la sesión de Windows iniciada (igual que Docker y Ollama).
- El video hay que grabarlo después del último cambio de interfaz.

## Preguntas que te pueden hacer

!!! pregunta "¿Qué pasa si se cae el internet durante la defensa?"
    Seguimos en `localhost:8080`: la base, la API, la voz y el modelo de lenguaje corren en la laptop. Solo se pierden el enlace
    público y las calles del mapa, que cae a un mapa de alcaldías.

!!! pregunta "¿Por qué el enlace es enlaza.zenthinks.com y no un servidor en la nube?"
    Porque para el prototipo la laptop cuesta cero y mantiene los datos locales. El túnel de Cloudflare publica la laptop
    con un certificado HTTPS válido sin abrir puertos del módem; en producción iría a un servidor (@ref(cap-negocio)).
