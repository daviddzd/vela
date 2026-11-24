# La biblia de Enlaza

PDF maestro que explica todo el proyecto para estudiarlo y defenderlo. Las fuentes viven aquí, en Markdown; el PDF,
el HTML intermedio y las capturas **no se suben a Git** (se regeneran).

## Generarla

Con `docker compose up -d` corriendo (la base de datos y la app deben estar arriba):

```bash
bash scripts/build_biblia.sh              # números + PDF  → docs/biblia/biblia_enlaza.pdf
bash scripts/build_biblia.sh --capturas   # además: reset_demo.py, capturas nuevas de cada pantalla, reset otra vez
```

La primera vez construye la imagen `vela-biblia` (Playwright + Python + Paged.js + Mermaid). Si no hay capturas,
las toma solas.

## Cómo se escribe un capítulo

- Orden del libro: `contenido.yaml`. Cada capítulo empieza con `# Título {#cap-id}`.
- Estructura fija: En una frase · Explicado sin tecnicismos · Por qué lo hicimos así · Cómo funciona por dentro ·
  Dónde está en el código · Números clave · Limitaciones honestas · Preguntas que te pueden hacer.
- **Ningún número a mano.** Escribe `{{ clave }}`; los valores salen de `build/collect_numbers.py`, que lee la
  semilla, la base, `config/`, `simulation/results/`, `voice/eval/results/`, `data/business/assumptions.csv`, constantes
  del código y `datos/mediciones_manuales.yaml`. Lista de claves: `out/numeros.csv` (después de generar).
  `{{ tabla clave1 clave2 }}` hace una tabla «Dato | Valor | Fuente». Una clave desconocida detiene la compilación.
- Términos: `[[término]]` o `[[término|texto]]`; deben existir en `glosario.yaml`.
- Referencias: `@ref(cap-id)` → «cap. N «Título» (p. X)».
- Capturas: `![Pie](capturas/nombre.png)`; `{.media}` o `{.celular}` al final para hacerlas más chicas.
- Cajas: `!!! pregunta "¿…?"`, `!!! nota "…"`, `!!! cuidado "…"`, `!!! ejemplo "…"`, `!!! frase "…"`.
- Datos del equipo (nombres, materias, defensa): `equipo.yaml`; vacío se imprime «____».

## Archivos

| Archivo | Qué es |
|---|---|
| `build/Dockerfile` | imagen de compilación |
| `build/collect_numbers.py` | junta todos los números con su fuente → `out/numeros.json`, `out/numeros.csv` |
| `build/build.py` | Markdown → `out/biblia.html` (marcadores, glosario, referencias); `out/numeros_usados.csv` |
| `build/render.cjs` | HTML → PDF (Mermaid, Paged.js, marcadores del PDF) |
| `build/capture.cjs` | capturas de cada pantalla por rol |
| `build/style.css` | diseño con la identidad Enlaza (`docs/brand.md`) |
