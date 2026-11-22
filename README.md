<p align="center"><img src="assets/brand/logo.svg" width="320" alt="Vela · cuidado coordinado"></p>

# Vela · cuidado coordinado

Prototipo académico de una plataforma web (SaaS) para que clínicas, residencias, centros de día y redes
de cuidado a domicilio de la Ciudad de México coordinen la atención de personas adultas mayores:
solicitudes de servicio, asignación automática de personal, seguimiento en tiempo real, tableros de
decisión, simulación de escenarios y un asistente de voz que detecta emergencias.

> **Proyecto escolar.** Licenciatura en Ciencia de Datos para Negocios, UNRC, 6.º semestre (2026-2).
> "Vela" es una empresa ficticia. **Todos los datos son sintéticos**, calibrados con fuentes públicas
> (INEGI, ENSANUT, ENASEM, CONAPO, SIMAT, TomTom). No contiene datos de personas reales.

## Módulos
| Módulo | Materia | Qué hace |
|---|---|---|
| Operación (TPS/CRM/ERP) | Sistemas de Información Empresarial | Solicitudes, pacientes, personal, asignación y aprobación |
| Panorama-AM (MIS/DSS) | Visualización | Tableros, mapa de riesgo, indicadores |
| SIRAG-D | Modelado y Simulación | Simulación de despacho con tráfico y contingencia ambiental |
| ORACLE-Voz | Cómputo Cognitivo | Voz → texto → triaje → reporte para el médico / pantalla 911 |
| Modelo de negocio | Emprendimiento | Planes de suscripción, costos, proyección |
| Ética y privacidad | Práctica Profesional | Consentimientos, aviso de privacidad, auditoría |

## Cómo correrlo
Guía completa: [`docs/00_preparar_laptop_y_github.md`](docs/00_preparar_laptop_y_github.md).

```bash
cp .env.example .env            # cambia las contraseñas y JWT_SECRET
docker compose up -d --build    # base de datos, migraciones, API, worker, web y proxy
python scripts/verify_db.py      # comprueba conteos, traslapes y aislamiento entre instituciones
docker compose exec api pytest -q   # pruebas de sesión y aislamiento entre instituciones
```

La aplicación queda en http://localhost:8080 (`/api` → API, `/ws` → WebSocket).
Decisiones técnicas de la base: [`docs/dev/decisiones_paso_1_2.md`](docs/dev/decisiones_paso_1_2.md).

Usuarios de prueba (contraseña de demostración pública `Demo2026!`): `owner@ejemplo.test`,
`coordinacion.a@ejemplo.test`, `cui-001@ejemplo.test`, `cui-003@ejemplo.test`, `fam-0001@ejemplo.test`.

## Documentación
- Especificación: [`docs/spec/00_indice.md`](docs/spec/00_indice.md)
- Identidad visual: [`docs/brand.md`](docs/brand.md)
- Aviso de privacidad y consentimiento: [`docs/legal/`](docs/legal/)

## Licencia
Código bajo licencia MIT. Datos sintéticos bajo CC BY 4.0. Las fuentes oficiales citadas conservan sus propias licencias.
