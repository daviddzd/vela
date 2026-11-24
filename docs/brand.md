# Identidad visual · Enlaza · cuidado coordinado

**Nombre:** Enlaza · cuidado coordinado. Empresa ficticia: **Enlaza Cuidado Coordinado** (proyecto escolar, UNRC,
LCDN 2026-2). Hasta el 23/11/2026 se llamó «Vela».
**Idea:** enlazar a la institución, al personal y a la familia alrededor de cada persona mayor (la cruz del cuidado
y un corazón con una palomita, entrelazados).
**Tono:** cálido, claro, respetuoso; frases cortas; hablar de "personas mayores", nunca "abuelitos" ni "ancianos".

## Nombres internos que NO cambian
Para no romper nada, el código y la infraestructura conservan el nombre anterior: el rol de base de datos
`vela_api` y `vela_owner`, la base `vela` / `vela_test`, la red y las imágenes de Docker (`vela_default`,
`vela-web`, `vela-backend`…), la carpeta del repositorio, el canal de eventos `vela_events` y nombres de código
como `oracle.py` o `vela_timeout`. Solo cambió lo que una persona lee: interfaz, títulos, favicon, documentos.
El módulo de voz se llama **Enlaza Voz** (antes ORACLE-Voz, marca registrada); `docs/spec/05_oracle_voz.md`
conserva su nombre de archivo.

## Logotipo
Original: `assets/brand/source/logo_enlaza.jpg`. Recreado con formas geométricas (no calco automático) por
`assets/brand/scripts/make_logo.py`, sobre una cuadrícula de 2048 unidades medida en el original:
cruz simétrica (1229 de ancho, brazos de 492, radio 115, trazo 82), corazón con dos semicírculos y lados a 45°,
palomita (brazo corto `x − y = −18`, cinta diagonal `x + y = 2045`, toda en teal) y división de color teal / azul
marino en `x + y = 2110`. Los huecos del entrelazado son máscaras, así que la versión blanca sirve sobre cualquier
fondo. Superpuesto con el original coincide en **92 %** (IoU por color: teal 90.7 %, azul marino 93.8 %).

| Archivo | Uso |
|---|---|
| `assets/brand/enlaza-logo.svg` | logo completo (símbolo + «Enlaza» + «cuidado coordinado», texto en trazos) |
| `assets/brand/enlaza-simbolo.svg` | solo el símbolo |
| `assets/brand/enlaza-logo-blanco.svg`, `enlaza-simbolo-blanco.svg` | para fondos oscuros |
| `assets/brand/enlaza-favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` (180 px), `enlaza-icono-512.png` | favicon e íconos |

Copias para la app en `frontend/public/` (`logo.svg`, `logo-white.svg`, `logo-mark.svg`, `favicon.svg`, PNG).
Para regenerarlos: `python3 assets/brand/scripts/make_logo.py` (necesita `fonttools` y `npm install` en `frontend/`).

## Colores
Teal y azul marino medidos con cuentagotas en el logo (mediana de los píxeles). Todo par texto/fondo se comprueba
con `python3 scripts/check_contrast.py` (WCAG AA: 4.5:1 texto, 3:1 texto grande, íconos y bordes).

| Token | Hex | Uso | Contraste |
|---|---|---|---|
| `teal` | `#2AAEAE` | teal del logo: degradados, fondos de círculos, decoración | 2.70 sobre blanco: **nunca texto ni íconos con significado** |
| `teal-text` | `#137273` | palabra destacada en títulos, íconos, anillo de foco | 5.70 sobre blanco |
| `teal-soft` | `#E3F5F5` | círculo suave detrás de los íconos | — |
| `navy` | `#3A5B76` | azul marino del logo: títulos, botones principales, enlaces | 7.15 sobre blanco |
| `navy-dark` | `#2C465C` | botón principal al pasar el cursor | 9.82 con texto blanco |
| `deep` | `#1B3349` | secciones de fondo azul profundo | 12.99 con texto blanco |
| `sky` / `sky-soft` | `#EAF4F8` / `#F4F9FB` | degradado azul muy claro de los encabezados de sección | — |
| `ink` / `muted` | `#1B2B38` / `#4F5F6B` | texto / texto secundario | 14.49 / 6.60 |
| `ok` / `warn` / `danger` | `#1D7447` / `#8A5A00` / `#B42318` | estados, **siempre con texto e ícono** | 5.77 / 5.93 / 6.57 |

Gráficas (`frontend/src/charts/theme.ts`), validadas con el validador de paletas (luminosidad, croma, daltonismo
protan/deutan/tritan, contraste): series `#0094A6` (teal profundo) · `#3159B8` (azul) · `#B23E89` (magenta, tercer
tono); todas ≥ 3:1 sobre blanco, peor par adyacente ΔE 8.2 con daltonismo, 17.6 con visión normal; contra los
colores de estado ΔE ≥ 15 con visión normal. Rampa secuencial `#6FBFC8 → #0A4F5C` (un tono, monótona).

## Tipografía
- **Títulos:** Plus Jakarta Sans 700/800 (SIL OFL, empaquetada con `@fontsource/plus-jakarta-sans`).
- **Texto:** Atkinson Hyperlegible 400/700 (SIL OFL), diseñada para baja visión. Base 18 px; modo sencillo 24 px.
- **Números:** todos los dígitos del sistema salen de Plus Jakarta Sans (cara «Enlaza Digits» con `unicode-range`
  solo de dígitos, primera en la pila): el cero es el mismo en cifras grandes, fechas, horas y claves; Atkinson lo
  dibuja cruzado («Ø»). Se quita con una línea en `frontend/src/index.css`.

## Componentes
- Tarjetas blancas, esquinas de 22 px, sombra suave (`--shadow-card`); cajas internas y campos con 14 px.
- Botones tipo píldora (`rounded-full`), al menos 48 px de alto, con texto + ícono.
- Íconos dentro de círculos de color suave (`IconCircle`).
- Títulos grandes con una palabra destacada en `teal-text` (`Highlight`: en `es.ts` va entre asteriscos,
  «Tablero \*en vivo\*»), sobre un encabezado con degradado azul claro (`PageHeader`, clase `section-header`).
- Franjas de cifras grandes (contadores del tablero, cifras de la página de presentación).
- Sin vidrio translúcido: los fondos son sólidos para no bajar el contraste.
- Estados con ícono y palabra ("En camino", "No cerrada"), nunca solo color.

## Página de presentación (`/`)
Pública; el inicio de sesión está en `/entrar`. Problema y propuesta, cifras con su fuente (las del prototipo dicen
«datos sintéticos»), cómo funciona, los cinco módulos, planes y precios (supuestos del modelo de negocio, Gobierno
aparte), privacidad y ética, y el pie «Prototipo académico · datos sintéticos». Prohibido: doctores, testimonios,
calificaciones o cifras inventadas; fotos de personas reales como si fueran personal. Créditos: `docs/creditos.md`.
