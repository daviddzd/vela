# 11 · Ética y privacidad (Práctica Profesional)

## Marco legal
- Ley Federal de Protección de Datos Personales en Posesión de los Particulares, publicada en el DOF el
  20 de marzo de 2025 y vigente desde el 21 de marzo de 2025. La autoridad es la Secretaría Anticorrupción
  y Buen Gobierno (sustituye al INAI). Los datos de salud son **datos personales sensibles**: requieren
  consentimiento expreso y por escrito.
- NOM-004-SSA3-2012 (expediente clínico) como referencia de confidencialidad; el prototipo no sustituye
  un expediente.

## Cómo lo cumple el prototipo
| Principio | Implementación |
|---|---|
| Consentimiento | Tres tipos (`health_data`, `home_care`, `voice_assistant`), con vigencia; si falta, la función se bloquea |
| Representación | Si la persona no puede decidir, firma su representante legal y se registra su asentimiento |
| Minimización | Cada rol ve solo lo necesario; el familiar ve solo a su paciente |
| Aislamiento | Seguridad a nivel de fila por institución, falla cerrada |
| Trazabilidad | `audit_log` de lecturas, cambios, aprobaciones e intentos bloqueados |
| Derechos ARCO | Pantalla `/privacidad` con instrucciones y formulario de solicitud |
| IA responsable | ORACLE-Voz no diagnostica; las decisiones de asignación alta y contingencia las aprueba una persona. Única excepción: una solicitud alta **urgente** sin respuesta en 3 min se aplica "por tiempo", con aviso a coordinación, registro en bitácora y posibilidad de cambiarla (ver riesgo 3) |
| Datos sintéticos | Ningún dato real; las grabaciones de prueba son propias con consentimiento o de licencia abierta |

Plantillas en `docs/legal/aviso_de_privacidad.md` y `docs/legal/formato_consentimiento.md`.

## Riesgos éticos a discutir en la defensa
1. Falsas alarmas vs. emergencias perdidas (se eligió priorizar no perder emergencias).
2. Sesgo de reconocimiento de voz por edad, acento y lengua indígena.
3. Automatización de asignaciones: quién responde si falla (por eso existe la aprobación humana). La
   simulación mostró que esperar una aprobación lenta empeora la respuesta a lo urgente; se eligió aplicar
   la propuesta solo en lo urgente y tras 3 min, dejando a la persona la última palabra (puede cambiarla)
   y la responsabilidad trazable en `audit_log` (`assignment_approved_by_timeout`).
4. Vigilancia del personal: los datos de llegada se usan para coordinar, no para sancionar.
