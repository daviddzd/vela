# Presentación y guion del coloquio

| Archivo | Qué es |
|---|---|
| `enlaza_coloquio.pptx` | la presentación (16:9, texto editable, gráficas nativas, notas del orador con el guion) |
| `enlaza_coloquio.pdf` | la misma presentación en PDF (respaldo si falla PowerPoint) |
| `guion_coloquio.md` / `.pdf` | guion minuto a minuto, demo paso a paso, plan B, 20 preguntas, checklist y video de respaldo |
| `guion_fuente.md` | **la fuente del guion** (se edita aquí; `guion_coloquio.md` se genera) |
| `fuentes/` | tipografías de la marca (Plus Jakarta Sans y Atkinson Hyperlegible, licencia SIL OFL) |
| `build/` | cómo se genera todo |

## Antes de abrirla en PowerPoint

Instalar las cuatro fuentes de `fuentes/` (doble clic en cada `.ttf` → Instalar). Sin ellas, PowerPoint pone otra letra y
algunos textos pueden moverse. En **Google Slides** no hace falta: las dos fuentes ya están ahí.

## Regenerarla

Con `docker compose up -d` corriendo:

```bash
bash scripts/build_presentacion.sh              # números + presentación + guion (+ capturas si no hay)
bash scripts/build_presentacion.sh --capturas   # además: reset_demo.py, capturas nuevas 16:9 de la demo, reset otra vez
```

- **Ningún número a mano:** salen de `docs/biblia/out/numeros.json` (el mismo script de la biblia). En el guion se escriben
  `{{ clave }}`; en las diapositivas, `T("clave")` en `build/deck.cjs`.
- El guion no puede pasar de **9:40** (10 min menos 20 s de margen): `render_guion.py` suma los «Dura» y se detiene si se pasa.
- Si se cambia un texto en PowerPoint, conviene pasarlo también a `build/deck.cjs` o `guion_fuente.md`; si no, la siguiente
  compilación lo regresa.
- Verificación (`out/verificacion.md`): cada número impreso aparece en su PDF, todo el texto mide 24 pt o más (salvo fuentes y
  número de diapositiva, 14 pt), no falta ningún carácter en las fuentes, nada se sale de la diapositiva y todas tienen notas.
- Imágenes de cada diapositiva para revisarlas: `out/diapositivas/`.
