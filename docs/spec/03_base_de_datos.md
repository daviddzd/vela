# 03 · Base de datos

Scripts en `database/sql/` (probados en PostgreSQL 16 el 20 nov 2026, salvo `005_postgis.sql`, que requiere
la imagen con PostGIS). Semillas en `database/seed/` y referencias en `data/reference/`.

## Tablas
| Capa | Tabla | Filas semilla | Para qué |
|---|---|---|---|
| Referencia | `districts` | 16 | Alcaldías con población 60+ (Censo 2020) |
| | `subscription_plans` | 3 | Básico, Profesional, Institucional |
| | `services` | 9 | Catálogo con precios de referencia de mercado |
| | `air_quality_stations` / `air_quality_readings` | 17 / 12,240 | Estaciones y lecturas horarias O₃ y PM2.5 |
| | `traffic_hourly_profile` | 48 | Congestión por hora, laborable y fin de semana |
| Instituciones | `institutions`, `institution_services` | 5 / 30 | Clientes (inquilinos) y sus servicios |
| CRM | `persons` | 20,000 | Población sintética 60+ (para tableros y simulación) |
| | `patients`, `family_members`, `consents` | 400 / 400 / 1,200 | Pacientes, familiares, consentimientos |
| ERP | `caregivers`, `caregiver_skills` | 44 / 49 | Personal y habilidades |
| | `users` | 31 | Cuentas de demostración |
| TPS | `care_plans` | 927 | Frecuencia de servicios por paciente |
| | `service_requests`, `assignments` | 2,864 / 2,597 | Historial de 30 días |
| En uso | `voice_reports`, `alerts`, `contingency_events`, `contingency_decisions`, `invoices`, `audit_log` | 0 | Se llenan al usar el sistema |

## Estados de una solicitud
`registered → validated → queued → assigned → in_progress → completed → closed`,
con salidas `rejected`, `cancelled`, `unattended`. En la semilla solo aparecen `closed`, `cancelled` y
`unattended` (≈9 % sin atender, a propósito: es el problema que el sistema debe reducir).

## Vistas
- `v_persons`: edad, grupo de edad, número de enfermedades crónicas, multimorbilidad, sensibilidad a contaminación.
- `v_patients`, `v_consents.is_valid`, `v_service_requests` (minutos para asignar, retraso, duración).
- `v_air_quality_24h`: promedio móvil de 24 h de PM2.5.

## Comprobaciones hechas
- 0 traslapes de horario por cuidador.
- 1,486 asignaciones automáticas y 1,111 aprobadas por coordinación (prioridad alta).
- Sin `app.institution_id` el rol de la API ve 0 pacientes; con `INS-A` ve 150; con `*` ve 400.
- Las contraseñas de los 31 usuarios verifican con `crypt('Demo2026!', password_hash)`.

## Reglas para cambios
Después de la carga inicial, todo cambio de esquema se hace con Alembic (`backend/migrations`) y se
documenta aquí.
