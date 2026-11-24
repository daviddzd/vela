# Visualización {#cap-m-vis}

<p class="responsable">Responsable: {{ equipo.materias.visualizacion }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **Panorama-AM y todas las pantallas de Enlaza se diseñaron para decidir y para cualquier persona: cada gráfica responde
    una pregunta, compara contra una referencia, dice su fuente, funciona con daltonismo y baja visión, y se lee igual en
    el proyector que en un celular.**

## Qué evalúa el profesor

Normalmente: que cada visualización responda una **pregunta**, la elección del **tipo de gráfica**, el uso del **color**,
la **honestidad** de ejes y escalas, la **accesibilidad**, los **tableros** (organización, jerarquía) y la capacidad de
**contar una historia** con los datos. (Confirmen con el programa del profesor.)

## Los conceptos, desde cero

### Visualizar para responder una pregunta

**Qué es.** Una gráfica no es decoración: existe para que alguien entienda algo y decida. Primero la pregunta, después la
gráfica.

**En Enlaza.** Cada tarjeta empieza con una pregunta («¿Estamos cumpliendo?», «¿Dónde vive la población 60+ con más
riesgo?») y un **número clave** grande que la responde (@ref(cap-panorama)).

### Codificación visual

**Qué es.** Cómo un dato se convierte en algo visible: posición, longitud, ángulo, área, color. El ojo compara mejor
**posición y longitud** que áreas o ángulos.

**Ejemplo.** Es más fácil ver qué barra es más larga que qué rebanada de pastel es más grande.

**En Enlaza.** Barras horizontales para comparar enfermedades (longitud), puntos con barras de error para comparar
políticas (posición), líneas para series en el tiempo. No hay gráficas de pastel.

### Tipos de gráfica y para qué sirve cada una

| Pregunta | Gráfica | En Enlaza |
|---|---|---|
| ¿Cómo cambia en el tiempo? | línea | puntualidad por día; O₃ y PM2.5 por hora |
| ¿Cuál es más grande? | barras | prevalencias; carga del personal |
| ¿Dónde? | mapa coroplético o de puntos | riesgo por alcaldía; visitas de hoy; estaciones |
| ¿Cuándo es peor? (dos dimensiones) | mapa de calor | tráfico: hora × tipo de día |
| ¿Qué tan seguro es? | punto con intervalo de confianza | comparación de políticas en `/simulacion` |
| ¿Cuánto ahora? | número grande | contadores del tablero |

### Color: categórico, secuencial y divergente

**Qué es.** **Categórico:** colores distintos para grupos sin orden. **Secuencial:** un tono de claro a oscuro para
«poco → mucho». **Divergente:** dos tonos que se alejan de un centro.

**En Enlaza.** Series con una paleta categórica validada (teal profundo, azul, magenta); coropletas con una **rampa
secuencial de un solo tono** (teal claro a teal oscuro); el teal del logo nunca se usa para texto porque no tiene contraste
suficiente. Detalle en `docs/brand.md`.

### Daltonismo y «nada solo con color»

**Qué es.** Algunas personas no distinguen rojo de verde (protan, deutan) o azul de amarillo (tritan). Si la información
depende solo del color, la pierden.

**En Enlaza.** La paleta se revisó con un validador (luminosidad, croma, daltonismo y contraste). Y cada estado lleva
**ícono y palabra** («Asignada», «En espera», «Fase I» con rombo, «Vigilancia» con triángulo).

### Contraste y WCAG

**Qué es.** [[WCAG]] son las pautas de accesibilidad web. Nivel AA: contraste de al menos 4.5:1 para texto normal y 3:1 para
texto grande, íconos y bordes.

**En Enlaza.** `scripts/check_contrast.py` revisa cada par texto/fondo de la marca; el criterio A13 pide Lighthouse ≥ 90 en
accesibilidad.

### Tipografía legible

**Qué es.** Algunas letras se confunden (I, l, 1; O, 0). Hay tipografías diseñadas para baja visión.

**En Enlaza.** Atkinson Hyperlegible (diseñada para baja visión) a 18 px; 24 px en el [[modo sencillo]]; dígitos de Plus
Jakarta Sans para que el cero no se vea cruzado.

### Honestidad en ejes y escalas

**Qué es.** Una gráfica puede mentir sin decir nada falso: barras que no empiezan en cero exageran diferencias; un **doble
eje** permite hacer que dos series «se crucen» donde uno quiera.

**En Enlaza.** Barras desde cero; O₃ y PM2.5 en **dos gráficas separadas**, cada una con su umbral de Fase I; las
diferencias de la simulación con su intervalo, no solo el promedio.

### Comparar contra una referencia

**Qué es.** Un número solo no dice si es bueno o malo. Hay que compararlo con algo: el pasado, una meta, una fuente oficial.

**En Enlaza.** Línea base contra «Con Enlaza»; población sintética contra ENSANUT/ENASEM; aire contra el umbral; políticas
contra el despacho humano. Y si hay pocos datos, no se compara: «datos insuficientes (N visitas)» con menos de
{{ code.min_visits_rate }}.

### Tableros (dashboards) y jerarquía

**Qué es.** Un tablero reúne varias visualizaciones para una tarea. Buena jerarquía: lo más importante arriba y grande;
lo de detalle, abajo o en una tabla.

**En Enlaza.** El tablero en vivo empieza con reloj y contadores, luego «¿Quién espera más?» y alertas, luego el mapa. En
Panorama: número clave → gráfica → nota y fuente → «Ver como tabla».

### Accesibilidad de las gráficas

**Qué es.** Que quien no puede ver la gráfica (lector de pantalla, baja visión) obtenga la misma información.

**En Enlaza.** Cada gráfica tiene una etiqueta de texto, «Ver como tabla», leyendas en HTML (no dentro del lienzo) y el
mapa repite su información en una lista.

### Diseño adaptable (responsive)

**Qué es.** Que la misma página funcione en pantallas de distintos tamaños.

**En Enlaza.** Probado a 390 px (celular) y 1280 × 720 (proyector) con capturas automáticas; el menú se vuelve un botón en
el celular; las gráficas no crecen solas (una de las correcciones de la revisión en Chrome).

### Mapas: coropleta, puntos y mosaicos

**Qué es.** **Coropleta:** regiones coloreadas por un valor. **Mapa de puntos:** cada elemento en su lugar. **Mosaicos:** el
fondo con calles se descarga en cuadritos.

**En Enlaza.** Coropleta por alcaldía en Panorama (límites oficiales del INEGI, CC BY 4.0); puntos con forma y palabra en el
tablero, el personal y la contingencia; calles de OpenFreeMap / OpenStreetMap; sin internet, cae a las alcaldías con un aviso.

### Contar una historia con datos

**Qué es.** Ordenar las visualizaciones para llevar a una conclusión: contexto → problema → evidencia → decisión.

**En Enlaza.** La demostración sigue esa historia: problema (Panorama, población y riesgo) → operación en vivo → contingencia
→ simulación que compara políticas → decisión que cambió el producto.

## Por qué lo hicimos así

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| ECharts | Gráficas en imagen | Interactivas (tooltip, tabla) y ligeras |
| Sin pasteles | Gráfica de pastel | Se comparan mal los ángulos |
| Rampa de un tono | Arcoíris | El arcoíris no tiene orden natural y confunde con daltonismo |
| Dos gráficas de contaminantes | Doble eje | El doble eje engaña |
| Leyendas en HTML | Leyenda dentro de la gráfica | Se enciman en el celular |
| «Datos insuficientes» | Porcentaje con 2 visitas | Un 100 % con dos visitas engaña |

## Dónde se ve en el sistema

| Concepto | Pantalla | Código |
|---|---|---|
| Pregunta + número clave + fuente | todas las tarjetas | `frontend/src/components/ChartCard.tsx` |
| Paleta validada | todas las gráficas | `frontend/src/charts/theme.ts`, `docs/brand.md` |
| Contraste | toda la app | `scripts/check_contrast.py` |
| Intervalos de confianza | `/simulacion` | `frontend/src/pages/simulation/` |
| Coropleta | `/panorama?vista=panorama` | `frontend/src/pages/panorama/PanoramaView.tsx` |
| Mapas con calles | `/tablero`, `/personal`, `/contingencia` | `frontend/src/components/StreetMap.tsx` |
| Modo sencillo | `/entrar` | `frontend/src/auth/simpleMode.ts` |
| Pruebas de navegador | — | `frontend/scripts/ui_checks.mjs` |

## Números clave

{{ tabla code.min_visits_rate code.on_time code.small_cell ref.air_stations ref.traffic_rows seed.districts repo.pages }}

## Limitaciones honestas

- No se probó con **lectores de pantalla** reales ni con personas mayores.
- El puntaje de **Lighthouse** (criterio A13) se revisa a mano.
- Los mapas con calles **dependen de internet**.
- Las gráficas de la simulación muestran el resultado de la corrida guardada, no se recalculan en vivo.

## Qué decir en 2 minutos

!!! frase "Guion de 2 minutos · Visualización"
    «En Enlaza cada gráfica existe para responder una pregunta. Por eso cada tarjeta empieza con la pregunta y un **número
    grande** que la responde, después la gráfica, la **fuente** y «Ver como tabla».

    Siempre **comparamos contra algo**: la línea base antes de Enlaza, la referencia oficial de la ENSANUT, el umbral de la
    contingencia o el despacho humano en la simulación, y ahí mostramos **intervalos de confianza**, no solo promedios. Y si
    hay muy pocos datos, el tablero lo dice en lugar de mostrar un 100 % engañoso.

    Diseñamos para **personas mayores y para daltonismo**: Atkinson Hyperlegible, modo sencillo de 24 píxeles, contraste AA
    comprobado con un script, una paleta validada para los tres tipos de daltonismo y **ningún estado comunicado solo con
    color**: siempre ícono y palabra. Evitamos los trucos que engañan: nada de doble eje, barras desde cero y una rampa de un
    solo tono para el mapa.»

## 10 preguntas difíciles

!!! pregunta "1. ¿Por qué no usaron gráficas de pastel?"
    Porque el ojo compara mal ángulos y áreas. Para comparar categorías, barras ordenadas: se compara longitud, que se lee
    con mucha más precisión.

!!! pregunta "2. ¿Por qué un solo tono en el mapa y no un arcoíris?"
    Porque un solo tono de claro a oscuro se lee naturalmente como «poco a mucho». El arcoíris no tiene orden perceptual y
    con daltonismo algunos colores se vuelven indistinguibles.

!!! pregunta "3. ¿Cómo comprobaron que se lee con daltonismo?"
    La paleta pasó un validador de luminosidad, croma, contraste y simulación de daltonismo (protan, deutan, tritan), con
    distancias de color medidas. Además, ningún estado depende solo del color.

!!! pregunta "4. ¿Qué es WCAG AA y cómo lo cumplen?"
    Las pautas de accesibilidad web; AA pide contraste de 4.5:1 para texto (3:1 para texto grande, íconos y bordes). Cada par
    de colores de la marca se revisa con `scripts/check_contrast.py`, botones de al menos 48 px y estados con texto.

!!! pregunta "5. ¿Por qué separar O₃ y PM2.5 en dos gráficas?"
    Porque tienen unidades y escalas distintas. Juntarlas exige doble eje, y el doble eje deja que quien hace la gráfica
    decida dónde «se cruzan»: engaña.

!!! pregunta "6. ¿Por qué muestran intervalos de confianza en la simulación?"
    Porque cada resultado viene de {{ cfg.replications }} réplicas con azar. Un promedio solo no dice si la diferencia es real;
    si los intervalos casi no se traslapan, la diferencia es confiable (y lo confirmamos con pruebas).

!!! pregunta "7. ¿Por qué a veces dice «datos insuficientes»?"
    Porque con muy pocas visitas un porcentaje engaña: dos visitas puntuales dan «100 %». Con menos de {{ code.min_visits_rate }}
    se muestra «datos insuficientes (N visitas)» y el número grande usa la línea base.

!!! pregunta "8. ¿Cómo funciona en el celular?"
    Diseño adaptable probado con capturas automáticas a 390 px: una columna, menú en botón, leyendas en HTML que no se
    enciman, gráficas que no crecen solas y botones grandes.

!!! pregunta "9. ¿Qué pasa si una persona no puede ver la gráfica?"
    Cada gráfica tiene «Ver como tabla» y una etiqueta de texto; el mapa repite sus puntos en una lista. La información nunca
    está solo en la imagen.

!!! pregunta "10. ¿Qué historia cuenta el tablero?"
    Contexto (dónde vive la población con más riesgo), operación (qué pasa ahora y si estamos cumpliendo), evidencia (la
    simulación compara políticas con intervalos) y decisión (lo que cambió el producto). Es el orden de la demostración.
