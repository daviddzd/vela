# 07 · Panorama-AM (Visualización, MIS/DSS)

Tableros con ECharts y mapa con MapLibre. Cada gráfica responde una pregunta y dice de dónde vienen los datos.

## Vista Operación (coordinación, tiempo real)
| Pregunta | Visual |
|---|---|
| ¿Qué está pasando ahora? | Reloj, contadores (en cola, en camino, en visita, terminadas hoy) |
| ¿Quién espera más? | Lista de cola ordenada por prioridad y minutos de espera, con semáforo + texto |
| ¿Dónde están las visitas? | Mapa: pacientes con visita hoy, cuidadores, estaciones de aire |
| ¿Estamos cumpliendo? | Línea de puntualidad y % sin atender, últimos 30 días |
| ¿Cómo va la carga del personal? | Barras de horas asignadas por cuidador vs. turno |

## Vista Panorama (dirección y coordinación)
| Pregunta | Visual |
|---|---|
| ¿Dónde vive la población 60+ con más riesgo? | Coropleta por alcaldía: % multimorbilidad, dependencia, sensibilidad a contaminación |
| ¿Qué enfermedades pesan más? | Barras de prevalencia (sintética vs. referencia ENSANUT/ENASEM) |
| ¿Cómo está el aire? | Serie horaria O₃ y PM2.5 por estación con línea de umbral de contingencia |
| ¿Cuándo es peor el tráfico? | Mapa de calor hora × tipo de día (TomTom) |
| ¿Qué política conviene? | Intervalos de confianza de SIRAG-D por política y escenario |

## Reglas de diseño
- Paleta de marca para categorías; estados verde/ámbar/rojo **siempre con texto e icono**.
- Escalas secuenciales de un solo tono (teal) para coropletas; leyenda con unidades.
- Cada tarjeta: título como pregunta, número clave grande, nota "Fuente: …" y "Datos sintéticos".
- Filtros: institución (solo dirección), alcaldía, rango de fechas.
- Probar en móvil (390 px) y en proyector.
