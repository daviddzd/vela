# Comandos {#anx-comandos}

Todos se corren en Ubuntu (WSL2) desde `~/proyectos/vela`, salvo los marcados como PowerShell.

| Para | Comando |
|---|---|
| Encender todo | `docker compose up -d` |
| Ver el estado | `docker compose ps` · `curl -s localhost:8080/api/health` |
| Ver los registros de un servicio | `docker compose logs -f api` (o `worker`, `db`, `voice`, `proxy`) |
| Reiniciar la API y el worker | `docker compose restart api worker` |
| Reconstruir tras un cambio de código | `docker compose up -d --build api web worker` |
| Apagar | `docker compose stop` |
| Verificar la base | `python3 scripts/verify_db.py` |
| Respaldar la base | `bash scripts/backup_db.sh [etiqueta]` |
| Restaurar un respaldo | `bash scripts/restore_db.sh backups/<archivo>.dump` |
| Limpiar los ensayos | `python3 scripts/reset_demo.py --dry-run` y luego sin `--dry-run` |
| Fechas vivas | `python3 scripts/rebase_dates.py` |
| Crear la base de pruebas | `python3 scripts/create_test_db.py` |
| Pruebas del backend | `docker compose exec api pytest -q` |
| Pruebas de la simulación | `docker compose run --rm sim pytest -q simulation/tests` |
| Correr SIRAG-D | `docker compose run --rm sim` (escribe `simulation/results/`) |
| Contraste de colores | `python3 scripts/check_contrast.py` |
| Pruebas de navegador | ver el encabezado de `frontend/scripts/ui_checks.mjs` |
| Generar esta biblia | `bash scripts/build_biblia.sh` · con capturas nuevas: `--capturas` |
| Enlace público (PowerShell) | `cloudflared tunnel --url http://localhost:8080` |
| QR del enlace | `qrencode -s 12 -o ~/qr_enlaza.png "<enlace>"` |
| Cargar el modelo de lenguaje (PowerShell) | `ollama run <modelo de OLLAMA_MODEL> "hola"` · `ollama ps` |
| Reloj de WSL2 atrasado (PowerShell) | `wsl --shutdown` y volver a abrir Ubuntu |
| Flujo de un cambio | `git switch -c fix/<tema>` → commit → `git push -u origin fix/<tema>` → `gh pr create` → pruebas → `gh pr merge N --squash --delete-branch` |
