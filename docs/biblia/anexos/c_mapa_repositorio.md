# Mapa del repositorio {#anx-mapa}

```
vela/
├── CLAUDE.md                  reglas del proyecto (para el equipo y para Claude Code)
├── README.md                  presentación
├── docker-compose.yml         todos los servicios
├── .env.example               variables de ejemplo (el .env real no se sube)
├── backend/                   API y worker (Python, FastAPI)
│   ├── app/main.py            arranque de la API
│   ├── app/core/              sesión, roles, seguridad, bitácora, eventos en tiempo real
│   ├── app/routers/           una ruta por recurso (requests, approvals, board, panorama, voice, privacy…)
│   ├── app/services/          reglas de negocio (dispatcher, operations, queue, labor, coverage, contingency, oracle…)
│   ├── app/worker.py          vuelta de cada minuto
│   ├── migrations/versions/   cambios de esquema (Alembic)
│   └── tests/                 pruebas del backend (pytest)
├── frontend/                  la página (React + Vite + TypeScript)
│   ├── src/pages/             una pantalla por archivo
│   ├── src/components/        piezas comunes (tarjetas, mapa, botones)
│   ├── src/i18n/es.ts         todos los textos en español
│   └── scripts/ui_checks.mjs  pruebas en un navegador real
├── simulation/                SIRAG-D (SimPy): sirag/, experiments/, results/, tests/
├── voice/                     servicio de voz: triage/ (Whisper + clasificador), eval/ (evaluación y resultados)
├── database/                  sql/ (esquema, vistas, seguridad por fila) y seed/ (semilla sintética)
├── data/                      generator/ (generadores), reference/ (aire, tráfico, prevalencias), voice/ (frases), business/ (supuestos)
├── config/                    simulation.yaml (parámetros compartidos) y emergency_rules.yaml (reglas de voz)
├── infra/                     Caddyfile y db-init.sh
├── business/model.ipynb       cuaderno del modelo de negocio
├── scripts/                   verify_db, reset_demo, rebase_dates, backup_db, restore_db, create_test_db, build_biblia…
├── assets/brand/              logotipo e identidad
└── docs/
    ├── spec/                  especificación (00–11)
    ├── dev/                   decisiones técnicas de cada paso y capturas de revisión
    ├── legal/                 aviso de privacidad y formato de consentimiento
    ├── diagnostico/           guía, consentimiento verbal y plantilla del diagnóstico de campo
    ├── biblia/                este libro (fuentes en Markdown; el PDF no se sube)
    └── privado/               documentos del curso y del equipo (Git lo ignora)
```
