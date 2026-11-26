# Decisiones que se descartaron {#cap-descartadas}

## En una frase

!!! frase "En una frase"
    **Para cada decisión grande hubo una alternativa razonable que se descartó; esta tabla las reúne en un solo lugar, con la
    razón y el capítulo donde se explica, porque «¿por qué no hicieron X?» es de las preguntas más comunes en una defensa.**

## Explicado sin tecnicismos

Elegir bien es también saber decir por qué **no** se eligió lo otro. Si un profesor propone una alternativa, la respuesta
ideal empieza con «la consideramos, y la descartamos porque…».

## Por qué lo hicimos así

Las alternativas están dispersas en los capítulos («Por qué lo hicimos así»). Aquí se juntan para estudiarlas de una vez.

## Cómo funciona por dentro

### Arquitectura y tecnología

| Alternativa descartada | Lo que se eligió | Por qué | Capítulo |
|---|---|---|---|
| Server-Sent Events o preguntar cada pocos segundos | WebSocket | Los túneles rápidos de Cloudflare no soportan SSE; el polling llega tarde y gasta | @ref(cap-tiempo-real) |
| Instalar todo en Windows | Docker Compose | Se enciende igual en cualquier laptop | @ref(cap-arquitectura) |
| SQLite, MySQL u hojas de cálculo | PostgreSQL + PostGIS | Seguridad por fila, `EXCLUDE`, `LISTEN/NOTIFY`, mapas | @ref(cap-arquitectura) |
| IA en la nube (de pago) | Whisper y Ollama en la laptop | Privacidad de la voz y costo cero | @ref(cap-voz) |
| Ollama dentro de Docker | Ollama en Windows | Usa la GPU integrada; en WSL2 sería solo CPU | @ref(cap-arquitectura) |
| Varios puertos públicos | Un puerto (Caddy :8080) | Un solo túnel y cookies sin trucos | @ref(cap-arquitectura) |
| Una app por rol | Una web adaptable | Nada que instalar; se comparte con un QR | @ref(cap-recorrido) |
| Shiny/R para el tablero (lo sugiere el PP) | React + ECharts con API en Python | Tiempo real, mapas y una sola app; la lógica analítica sigue en Python; **confirmar con el profesor de Visualización** | @ref(cap-m-vis) |
| Reloj simulado acelerado en la app | Reloj real | La demostración ocurre de verdad; lo acelerado solo en la simulación | @ref(cap-tiempo-real) |

### Datos y seguridad

| Alternativa descartada | Lo que se eligió | Por qué | Capítulo |
|---|---|---|---|
| Datos reales de una institución | Datos sintéticos calibrados | Datos de salud sensibles; repositorio público | @ref(cap-datos) |
| Sortear cada enfermedad por separado | Cópula gaussiana | Multimorbilidad realista | @ref(cap-datos) |
| Filtrar por institución en el código | Seguridad por fila en PostgreSQL | Un olvido en una consulta no expone datos | @ref(cap-seguridad) |
| Conectar la API como dueña de las tablas | Usuario `vela_api` | El dueño se salta la seguridad por fila | @ref(cap-seguridad) |
| Responder 404 entre instituciones (Avance 2) | 403 + bitácora | Registrar el intento | @ref(cap-seguridad) |
| Bases de datos separadas por institución | Una base con RLS | Más simple de operar; aislamiento probado | @ref(cap-m-sie) |
| Token en el almacenamiento del navegador | Cookie httpOnly | JavaScript no la puede leer | @ref(cap-seguridad) |
| Un solo «acepto todo» | Tres consentimientos por tipo | Aceptar visitas sin aceptar la voz | @ref(cap-etica) |
| Guardar el audio | Solo la transcripción | Minimización de datos | @ref(cap-voz) |

### Operación y simulación

| Alternativa descartada | Lo que se eligió | Por qué | Capítulo |
|---|---|---|---|
| La coordinadora asigna todo (Avance 2) | Asignación automática + aprobación en lo de prioridad alta | Lo urgente esperaba más | @ref(cap-operacion) |
| Automatizar todo, sin aprobación | Aprobación humana en lo de prioridad alta | IA responsable; responsabilidad trazable | @ref(cap-etica) |
| Esperar siempre a la coordinadora | Límite de tiempo solo para lo urgente | Hallazgo de SIRAG-D | @ref(cap-sirag) |
| Elegir por distancia | Elegir por tiempo con el tráfico de la hora | La hora cambia el tiempo de viaje | @ref(cap-operacion) |
| Revisar traslapes solo en el código | Restricción `EXCLUDE` | Dos peticiones simultáneas | @ref(cap-operacion) |
| Dejar sin atender los servicios de 12 h | Relevos | Cumplir la jornada legal | @ref(cap-operacion) |
| Cambiar la plantilla ilegal automáticamente | Marcarla y avisar | La plantilla la decide la institución | @ref(cap-operacion) |
| Copiar la lógica de asignación en la simulación | Importar el mismo despachador | Las conclusiones valen para el sistema real | @ref(cap-sirag) |
| ANOVA de una vía o Kruskal-Wallis | Friedman + Wilcoxon con Holm | Muestras pareadas, no normales | @ref(cap-sirag) |
| Aleatorización sesgada o *hotfix* en una crisis (incidente del PP) | Reglas validadas en simulación + aprobación humana | Variables no validadas pueden desestabilizar | @ref(cap-m-sim) |

### Voz

| Alternativa descartada | Lo que se eligió | Por qué | Capítulo |
|---|---|---|---|
| Solo reglas | Reglas + clasificador | Las reglas solas detectan {{ voz.holdout.sens_rules }} de las emergencias del holdout | @ref(cap-voz) |
| Solo clasificador | Reglas primero; el clasificador nunca baja una regla | Predecibilidad en lo evidente | @ref(cap-voz) |
| Una sola pantalla roja | Dos niveles (rojo y ámbar) | Casi la mitad de las rojas habrían sido falsas | @ref(cap-voz) |
| Subir el umbral del clasificador | Mantenerlo | Bajaría la sensibilidad | @ref(cap-voz) |
| Adoptar el clasificador v2 | Mantener v1 | No cumplió la regla escrita antes del holdout | @ref(cap-voz) |
| Detectar deterioro cognitivo o ansiedad por el habla (incidente del PP) | Detectar urgencia y solicitudes de auxilio | Riesgo de confundir rasgos lingüísticos con síntomas | @ref(cap-m-cc) |
| Esperar el reporte para mostrar el 911 | El 911 primero | El reporte tarda decenas de segundos | @ref(cap-voz) |

### Visualización y negocio

| Alternativa descartada | Lo que se eligió | Por qué | Capítulo |
|---|---|---|---|
| Gráficas de pastel | Barras | Se comparan mal los ángulos | @ref(cap-m-vis) |
| Doble eje O₃ / PM2.5 | Dos gráficas | El doble eje engaña | @ref(cap-panorama) |
| Arcoíris en la coropleta | Rampa de un tono | Orden natural; daltonismo | @ref(cap-m-vis) |
| Mostrar el porcentaje con pocas visitas | «Datos insuficientes (N visitas)» | Evitar el espejismo del promedio | @ref(cap-panorama) |
| Comisión por servicio | Suscripción por tamaño | Ingreso predecible; asistencia privada | @ref(cap-negocio) |
| Mercado: total del sector | DENUE por segmento | Solo los que serían clientes | @ref(cap-negocio) |
| Escalamiento nacional (incidente del PP) | Expansión regional con tope | El mercado y la voz no lo sostienen | @ref(cap-m-emp) |

## Dónde está en el código

Cada fila apunta a su capítulo, y ahí está el código.

## Números clave

{{ tabla voz.holdout.sens_rules vozb.holdout.all_emergency_screens vozb.holdout.false_alarms bm.sc.base.npv25 bm.sc.recommended.npv25 }}

## Limitaciones honestas

- Algunas alternativas no se probaron a fondo (por ejemplo, rutas reales por calle o tráfico en vivo); se descartaron por
  alcance, no porque se demostrara que eran peores.

## Preguntas que te pueden hacer

!!! pregunta "¿Por qué no usaron una herramienta de tableros como Power BI o Shiny?"
    Porque el tablero debía ser parte de la misma app, en tiempo real, con la misma seguridad por fila y con mapas de la
    operación en vivo. Un tablero externo leería los datos por otra puerta. El PP sugiere Shiny o Python: toda la lógica analítica
    está en Python (API, simulación, cuaderno) y la interfaz solo dibuja; lo confirmaremos con el profesor de Visualización.

!!! pregunta "¿Consideraron no usar IA en la voz?"
    Sí: con solo reglas, en el holdout se detectaban {{ voz.holdout.sens_rules }} de las emergencias. El clasificador agrega las que
    las reglas no prevén. A cambio de falsas alarmas, que mitigamos con el aviso ámbar y la revisión humana.
