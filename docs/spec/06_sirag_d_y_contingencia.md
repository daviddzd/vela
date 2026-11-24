# 06 · SIRAG-D y contingencia (Modelado y Simulación)

**SIRAG-D** = Simulación de Riesgo Ambiental y Gestión de Despacho. Responde: *¿qué política de
asignación atiende mejor a los pacientes de mayor riesgo cuando hay contingencia ambiental y tráfico?*
Parámetros en `config/simulation.yaml`.

## Modelo (eventos discretos + agentes, SimPy)
- **Pacientes (agentes):** estado de salud en cadena de Markov por hora: `stable → at_risk → crisis`.
  Probabilidades base 0.0006, 0.05 (regreso) y 0.01 por hora, multiplicadas por factores de riesgo del
  paciente (enfermedad pulmonar 1.5, cardiaca 1.4, EVC 1.3, diabetes 1.15, dependencia severa 1.6,
  80+ 1.3) — **supuestos** documentados.
- **Contaminación:** por cada +10 µg/m³ de PM2.5 sube el riesgo de crisis: respiratorio 2.2 %, EPOC 1.6 %,
  cardiovascular 0.78 %, causas naturales 0.91 % (metaanálisis citados en el YAML).
- **Solicitudes:** salen de los planes de cuidado y de las crisis (prioridad alta).
- **Cuidadores (recursos):** turnos y habilidades reales de la semilla; viaje = distancia euclidiana ×
  1.4 (circuidad) ÷ velocidad de la hora (perfil TomTom 2025) × factor del escenario.
- **Despacho:** 4 políticas
  1. `nearest` – el más cercano disponible;
  2. `risk_priority` – primero los pacientes de mayor riesgo;
  3. `risk_plus_live_traffic` – riesgo + tiempo de viaje con tráfico de la hora (política de Enlaza);
  4. `human_dispatcher` – como hoy: por orden de llegada, con 5–20 min de retraso para decidir.

## Escenarios
| Escenario | Qué cambia |
|---|---|
| `normal` | Lecturas y tráfico típicos |
| `contingency_east` | PM2.5 alto en el oriente (SAC, UIZ…), rampa de 20 min |
| `contingency_east_roadblocks` | Lo anterior + bloqueo en Iztapalapa (09007), tráfico × 1.25 |

## Experimento
4 políticas × 3 escenarios × **30 réplicas** de 7 días, semilla 2026, intervalos de confianza al 95 %.
Métricas: tiempo de espera de prioridad alta (media y p90), % de crisis atendidas en < 60 min,
% sin atender, km recorridos, utilización del personal, horas extra.
Validación: con escenario `normal` y política `human_dispatcher` el porcentaje sin atender debe quedar
cerca del 9 % observado en el historial de 30 días. Prueba de hipótesis: ANOVA o Kruskal-Wallis entre
políticas y comparación por pares contra `human_dispatcher`.

Salidas en `simulation/results/` (CSV + gráficas) que se muestran en `/simulacion`.

## Contingencia en la operación real (reloj real)
1. `worker` revisa cada minuto las lecturas: O₃ ≥ 155 ppb (1 h) o PM2.5 ≥ 97.5 µg/m³ (promedio 24 h) →
   Fase I; ≥ 85 % del umbral → vigilancia.
2. Crea `contingency_events` y una **propuesta**: subir prioridad de pacientes sensibles en alcaldías
   afectadas, adelantar visitas de oxigenoterapia, avisar a familias, recalcular rutas con tráfico extra.
3. Coordinación ve la propuesta en `/contingencia` y aprueba total, parcial o la rechaza
   (`contingency_decisions`). Nada cambia sin aprobación.
4. Al terminar el evento todo vuelve a la prioridad base.
