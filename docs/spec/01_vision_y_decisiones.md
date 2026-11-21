# 01 · Visión y decisiones

## Problema
En la CDMX viven cerca de 1.49 millones de personas de 60 años o más. Las instituciones que las cuidan
(clínicas, residencias, centros de día y redes de cuidado a domicilio) coordinan visitas con llamadas,
WhatsApp y hojas de cálculo: se pierden solicitudes, no se sabe quién está disponible y no hay datos para decidir.

## Propuesta
**Vela** es una plataforma SaaS: cada institución contrata un plan mensual y obtiene en una sola web
la operación diaria, tableros, simulación de escenarios y un asistente de voz.

## Identidad (provisional; se puede cambiar)
- Nombre: **Vela · cuidado coordinado** (empresa ficticia "Vela Cuidado Coordinado").
- Idea: una vela acompaña y alumbra; el sistema "hace visible" lo que pasa con cada persona.
- Detalles visuales en [`docs/brand.md`](../brand.md).

## Decisiones cerradas
| Tema | Decisión |
|---|---|
| Ejecución | Todo local en la laptop Ryzen (Windows 11 + WSL2 + Docker). Acceso público con túnel de Cloudflare. |
| Reloj | Tiempo real, zona `America/Mexico_City`. La simulación acelerada solo corre fuera de línea. |
| Asignación | Automática para todas las solicitudes. Prioridad alta → el coordinador aprueba. |
| Idioma | Código en inglés; todo lo que leen personas (UI, documentos, reportes) en español. |
| Repositorio | Público en GitHub, con datos sintéticos incluidos y sin secretos. |
| Datos | Sintéticos, calibrados con fuentes oficiales reales (ver 09). |
| Tiempo real | WebSockets (los túneles rápidos de Cloudflare no soportan SSE). |
| IA local | Ollama (LLM) + faster-whisper (voz) en la laptop; sin servicios de pago. |
| Multiinstitución | Una base de datos con seguridad a nivel de fila por `institution_id`. |

## Fuera de alcance (se menciona como trabajo futuro)
Pagos reales, facturación CFDI, app móvil nativa, llamada telefónica real al 911, integración con
expedientes clínicos externos.
