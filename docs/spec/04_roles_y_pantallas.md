# 04 · Roles, flujos y pantallas

## Roles
| Rol | Ve | Puede |
|---|---|---|
| Dirección Vela (`owner`) | Todas las instituciones (agregado) | Ver negocio, contingencia global, panel de demostración |
| Coordinación (`coordinator`) | Su institución | Aprobar asignaciones de prioridad alta, reasignar, decidir contingencias, ver tableros |
| Médico (`physician`) | Sus pacientes | Revisar reportes de ORACLE-Voz, ajustar planes de cuidado |
| Cuidador/enfermería (`caregiver`) | Sus visitas del día | Marcar llegada y término, enviar nota de voz |
| Familiar (`family`) | Su paciente | Solicitar servicio, confirmar visita, usar asistente de voz |

## Flujo principal: solicitud → visita
1. Una solicitud nace del plan de cuidado (worker), de un familiar, de coordinación o de ORACLE-Voz.
2. Validación: paciente activo, consentimiento vigente, servicio activo, sin duplicado en ±2 h.
3. El despachador calcula candidatos (habilidad, turno, sin traslape, distancia × tráfico de la hora)
   y elige con la política activa (por defecto `risk_plus_live_traffic`).
4. Prioridad baja/media → se asigna al momento. Prioridad alta → aparece en **Aprobaciones** con el
   candidato propuesto y dos alternativas; coordinación aprueba o cambia.
   **Excepción (hallazgo de SIRAG-D):** si una solicitud alta **urgente** (visita en menos de 60 min) lleva
   3 min sin aprobación, se aplica el candidato propuesto ("aprobada por tiempo"), se avisa a coordinación y
   queda en la bitácora; coordinación puede cambiarla. Las visitas altas programadas siempre esperan a una persona.
5. El cuidador marca llegada y término; el familiar confirma.
6. Si nadie está disponible: queda en cola, se reintenta cada minuto (la visita puede empezar hasta 60 min
   después de la hora pedida) y se alerta a los 30 min; pasada esa tolerancia queda "sin atender".

## Pantallas
| Ruta | Pantalla | Rol |
|---|---|---|
| `/` | Inicio de sesión (con "modo sencillo") | todos |
| `/tablero` | Tablero en vivo: reloj, cola, visitas en curso, alertas, mapa | coordinación |
| `/aprobaciones` | Propuestas de prioridad alta | coordinación |
| `/pacientes`, `/pacientes/:id` | Ficha, plan de cuidado, historial, consentimientos | coordinación, médico |
| `/personal` | Cuidadores, turnos, carga | coordinación |
| `/mis-visitas` | Agenda del día, botones grandes Llegué / Terminé / Nota de voz | cuidador |
| `/familia` | Estado de la próxima visita, solicitar servicio, asistente de voz | familiar |
| `/voz` | Grabar → resultado → pantalla 911 si aplica | familiar, cuidador |
| `/reportes-voz` | Bandeja de reportes para el médico | médico |
| `/panorama` | Panorama-AM | coordinación, dirección |
| `/simulacion` | Resultados SIRAG-D y comparación de políticas | coordinación, dirección |
| `/contingencia` | Estado ambiental, propuesta de ajustes, aprobar | coordinación, dirección |
| `/negocio` | Planes, ingresos, costos, proyección | dirección |
| `/privacidad` | Aviso de privacidad, consentimientos, bitácora | todos / dirección |
| `/demo` | Panel para cambiar el "mundo" en la presentación | dirección |

## Panel de demostración (`/demo`)
Botones: activar escenario `contingency_east`, `contingency_east_roadblocks`, volver a `normal`;
crear solicitud urgente; poner a un cuidador fuera de servicio; enviar frase de voz de ejemplo.
El panel solo cambia datos de entrada (lecturas, tráfico, disponibilidad); el sistema detecta,
propone y coordinación aprueba como en la operación real. Todo cambio queda marcado `origin='demo_scenario'`.

## Accesibilidad
Tipografía Atkinson Hyperlegible 18 px (24 px en modo sencillo), contraste AA, botones ≥ 48 px,
textos cortos, iconos con texto, nada se comunica solo con color.
