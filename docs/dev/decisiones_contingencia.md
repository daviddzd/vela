# Decisiones técnicas · contingencia en vivo y panel de demostración

Rama `feature/contingencia` (completa el paso 6). Migración `0006_live_contingency.py`.

## 1. Lecturas de "ahora"
`app/services/air_model.py` reproduce el modelo calibrado de `data/generator/build_reference_data.py`
(nivel diario de la ciudad, forma horaria, factor de estación, ruido lognormal). Cada sorteo usa una semilla
derivada de (2026, fecha, hora, estación): la misma hora siempre da el mismo valor. Cada minuto el worker
agrega lo que falte hasta la hora actual (`source = 'synthetic_calibrated'`). El modelo original no tiene
efecto por día de la semana y no se inventó uno.

## 2. Detección
Cada minuto: O₃ de la hora ≥ 155 ppb o PM2.5 promedio de 24 h ≥ 97.5 µg/m³ → Fase I; ≥ 85 % → vigilancia
(`config/simulation.yaml`). Se crea `contingency_events` (sin datos personales), una alerta para todos y un
evento `contingency.changed` por WebSocket. **Sin parpadeo:** un evento real termina cuando todas las
estaciones llevan 2 lecturas horarias seguidas debajo de vigilancia.

## 3. Propuesta y aprobación
- La propuesta es **por institución** (`contingency_proposals`, con seguridad por fila): subir prioridad de
  pacientes sensibles (pulmonar, cardiaca, EVC) en alcaldías afectadas → adelantar oxigenoterapia (48 h) →
  recalcular rutas de hoy si hay tráfico degradado → avisar a familias. Cada cambio con su motivo; si una
  categoría no tiene cambios, la pantalla dice por qué (se revisó).
- **Nada cambia sin aprobación.** Coordinación aprueba todo, una parte o nada (`contingency_decisions`);
  Dirección ve todo pero no decide; otra institución recibe 403 y queda en la bitácora.
- Subir prioridad usa `priority_overrides`: la `base_priority` del paciente nunca se modifica. Al terminar el
  evento se desactivan las excepciones y las solicitudes en cola regresan a su prioridad original.
- Bitácora: `contingency_detected`, `contingency_proposed`, `contingency_decided`, `contingency_applied`,
  `contingency_reverted`, `contingency_ended`.

## 4. Real y demostración nunca se mezclan
- Las lecturas de un escenario se guardan en `air_quality_scenario`; la vista `v_air_quality_live` las pone
  delante **solo mientras su escenario está activo**. El historial calibrado nunca se sobrescribe; en
  Panorama-AM el periodo se marca "Escenario de demostración".
- La detección real usa solo las lecturas calibradas; la de demostración usa la vista en vivo. Cada una con su
  propio evento (`run_id`) y su propia propuesta. "Volver a normal" desactiva el escenario y cierra **solo**
  el evento de demostración, de inmediato.
- PM2.5 se evalúa con promedio de 24 h: el escenario escribe las últimas 24 h ("episodio ya formado"); si
  no, la Fase I tardaría un día en aparecer. Medido: detección en 8–44 s.

## 5. Panel `/demo` (solo Dirección)
Cambia **datos de entrada**: lecturas, condición de tráfico (×1.25 y +15 min en viajes que cruzan
Iztapalapa), cuidadores fuera de servicio y una solicitud urgente (`origin = 'demo_scenario'`). Al dejar a un
cuidador fuera de servicio, sus visitas pendientes se vuelven a despachar con la misma lógica (las de
prioridad alta pasan por aprobación o por el límite de tiempo) y se alerta a coordinación. La institución
por omisión es la primera con personal en turno a esa hora.

## 6. Mapas sin internet
Los mapas de `/contingencia` y del tablero se dibujan con los límites oficiales de alcaldías (mismo GeoJSON de
Panorama-AM) y no dependen de mosaicos. Las alcaldías afectadas se sombrean por nivel; las estaciones son
puntos con forma distinta por nivel y solo las que están en vigilancia o Fase I llevan etiqueta (alternadas
izquierda/derecha para no encimarse); la leyenda usa ícono y palabra.
