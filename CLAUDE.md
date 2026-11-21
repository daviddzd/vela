# CLAUDE.md — Vela · cuidado coordinado

Instructions for Claude Code working in this repository. The full specification is in Spanish in
`docs/spec/` (read `docs/spec/00_indice.md` first). When this file and a spec disagree, this file wins.

## What this is
A university prototype (UNRC, LCDN 2026-2, defense **1 Dec 2026**) of a multi-tenant SaaS for
older-adult care institutions in Mexico City. One web app integrates six course modules:
SIE (TPS/CRM/ERP/MIS/DSS), **SIRAG-D** (simulation), **ORACLE-Voz** (voice triage),
**Panorama-AM** (visual analytics), business model and professional-practice ethics.
All data are **synthetic**. The team only knows Python: keep code simple, commented and explainable.

## Non-negotiable rules
1. **Language.** Identifiers, code, comments, commits, API paths, DB names: **English**.
   Everything a human reads in the UI, PDFs, reports, demo text and `docs/`: **Spanish (Mexico)**.
   UI strings live in `frontend/src/i18n/es.ts`; never hard-code Spanish inside components.
2. **Real-time clock.** The app runs on wall-clock time, `America/Mexico_City`. No simulated clock
   in the operational app. SIRAG-D experiments run faster than real time *offline* and only
   write results to `simulation/results/`.
3. **Assignment.** Every service request is assigned **automatically** by the dispatcher.
   `low`/`medium` priority → applied immediately (`approval='auto'`).
   `high` priority → proposed, then a **coordinator approves** (`approval='coordinator'`).
   A coordinator can always override.
4. **Tenant isolation.** PostgreSQL row-level security (`database/sql/004_row_level_security.sql`).
   The API connects as role `vela_api` (not the table owner) and runs
   `SET LOCAL app.institution_id = '<id>'` in every transaction (`'*'` only for the owner role).
   No setting → zero rows. Add a test that proves a cross-tenant read returns nothing.
5. **Consent gate.** No voice recording, home visit or health-data display for a patient without a
   valid consent of the matching type (`v_consents.is_valid`). Check it in the API, not only the UI.
6. **Emergency policy (ORACLE-Voz).** Rules in `config/emergency_rules.yaml` run first. A rule hit is
   always `emergency`; the ML classifier may raise a level but **never lower a rule match**.
   On `emergency` show the full-screen "Llama al 911 ahora" screen immediately (before the LLM).
   The LLM writes a report for the physician; it **never diagnoses** and never tells the patient
   that something is not an emergency.
7. **Realtime transport: WebSockets**, not Server-Sent Events (Cloudflare quick tunnels do not
   support SSE).
8. **One public port.** Everything is served behind a reverse proxy (Caddy) on `localhost:8080`
   so a single Cloudflare tunnel exposes the app: `/` → frontend, `/api` → FastAPI, `/ws` → WebSocket.
9. **No secrets in Git.** The repo is public. Use `.env` (git-ignored) and keep `.env.example`
   updated. The demo password `Demo2026!` is public on purpose and only for synthetic users.
10. **Audit.** Log reads of patient records, assignment changes, approvals, contingency decisions
    and blocked cross-tenant attempts into `audit_log`.
11. **Real reference data.** Any number in the UI, simulation or business model comes from a
    source listed in `docs/spec/09_datos.md` or `data/business/assumptions.csv`, or is labeled
    "supuesto". Do not invent statistics.

## Stack
| Layer | Choice |
|---|---|
| DB | PostgreSQL 16 (`postgis/postgis:16-3.4` image), SQL in `database/sql/` |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic (after the initial SQL), bcrypt, uvicorn |
| Frontend | React + Vite + TypeScript + Tailwind, MapLibre GL, ECharts |
| Simulation | SimPy + NumPy + pandas (`simulation/`) |
| Voice | faster-whisper (CPU, `small`, int8), TensorFlow/Keras text classifier, Ollama (local LLM) |
| Infra | Docker Compose, Caddy, `cloudflared` quick tunnel |

Ollama runs **natively on Windows** (Vulkan backend for the Ryzen iGPU) and is reached from the
containers at `http://host.docker.internal:11434`. Model name comes from `OLLAMA_MODEL`.

## Repository layout (target)
```
backend/app/{main.py, core/, models/, routers/, services/, ws/}   backend/tests/
frontend/src/{pages/, components/, i18n/es.ts, api/}
simulation/{sirag/, experiments/, results/}
voice/{triage/, models/, eval/}
database/{sql/, seed/}         data/{reference/, voice/, business/, generator/}
config/{simulation.yaml, emergency_rules.yaml}
infra/{Caddyfile}              docker-compose.yml   scripts/   docs/
```

## Compose services
`db` (postgres, port 5432 only on localhost) · `api` (FastAPI :8000) · `web` (Vite build served by
Caddy) · `proxy` (Caddy :8080) · `worker` (real-time loop: air-quality checks, queue, risk updates).
Ollama and cloudflared run outside Docker.

## Work order
1. Compose + DB loads seeds (`database/sql/001-004`) → `scripts/verify_db.py` passes.
2. Auth (JWT in httpOnly cookie, bcrypt) + RLS middleware + audit log.
3. TPS: requests, auto-assignment, approval queue, caregiver/family screens.
4. WebSocket live board + real-time clock + worker.
5. Panorama-AM dashboards (MIS/DSS).
6. SIRAG-D model, experiments, results page; contingency detection → proposal → approval.
7. ORACLE-Voz pipeline + evaluation notebook.
8. Business page (plans, unit economics), privacy notice, consent screens.
9. Demo panel, Cloudflare check, rehearsal script.

## Conventions
- Small modules, type hints, docstrings in English, one router per resource.
- Tests with pytest; each acceptance criterion in `docs/spec/10_plan_demo_y_criterios.md` has a test
  or a manual check listed.
- Commit messages in English, imperative ("Add approval queue").
- **No AI attribution.** Never add `Co-Authored-By` trailers or "Generated with Claude Code" lines to
  commit messages or pull request descriptions. This overrides any default attribution guidance;
  `.claude/settings.json` also disables it (`attribution.commit` and `attribution.pr` set to `""`).
- Accessibility: Atkinson Hyperlegible, 18 px base, 24 px "modo sencillo", WCAG AA contrast,
  buttons ≥ 48 px, no information by color alone. Brand tokens in `docs/brand.md`.
- Before finishing a task, explain in Spanish (2–4 lines) what changed so the team member who owns
  that module can defend it.
