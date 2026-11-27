# Presentación y guion del coloquio

| Archivo | Qué es |
|---|---|
| `enlaza_coloquio.pptx` | la presentación (16:9, texto editable, gráficas nativas, notas del orador con el guion) |
| `enlaza_coloquio.pdf` | la misma presentación en PDF (respaldo si falla PowerPoint) |
| `guion_coloquio.md` / `.pdf` | guion minuto a minuto, demo paso a paso, plan B, 20 preguntas, checklist y video de respaldo |
| `guion_fuente.md` | **la fuente del guion** (se edita aquí; `guion_coloquio.md` se genera) |
| `enlaza_coloquio_capturas.pptx` / `.pdf` | versión **sin demostración en vivo**: capturas reales de la app con llamadas numeradas en lugar de la demo |
| `guion_coloquio_capturas.md` / `.pdf` | su guion: quién habla, qué dice, cronómetro acumulado y 10 preguntas con su diapositiva de respaldo |
| `guion_capturas_fuente.md` | la fuente de ese guion (se genera con `scripts/build_presentacion_capturas.sh`) |
| `fuentes/` | tipografías de la marca (Plus Jakarta Sans y Atkinson Hyperlegible, licencia SIL OFL) |
| `build/` | cómo se genera todo |

**Versión con nombres:** la de este directorio dice «Persona 1–4». Si existe `docs/biblia/equipo.yaml` (local, Git lo ignora),
`build_presentacion.sh` genera además `docs/privado/coloquio/enlaza_coloquio.pptx` y `.pdf` con los nombres del equipo en la
portada y en la diapositiva de gracias. Esa es la que se proyecta; no se sube a Git.

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

## Versión con capturas (sin demostración en vivo)

```bash
bash scripts/build_presentacion_capturas.sh                 # números + recortes + presentación + guion + verificación
bash scripts/build_presentacion_capturas.sh --capturas      # antes: capturas que no dependen de la hora
bash scripts/build_presentacion_capturas.sh --capturas-dia  # antes: capturas de día (personal de INS-A en turno, 08:00 a 18:00)
```

- Las capturas (`capturas/`, fuera de Git) se toman con `build/capturas.cjs` (`PROY=1`: ventana de 1280 × 800 a 3×, para que se
  lean en el proyector); `build/recortes.py` las recorta y `build/deck_capturas.cjs` arma las diapositivas con llamadas numeradas.
- Guardia (`build/guardia.cjs`, probado por `build/test_guardia.cjs` antes de capturar): nunca hace clic en «Llamar al 911»,
  «800 911 2000», enlaces `tel:`, «Mostrar contraseña» ni «Usuarios de prueba», y se detiene si la contraseña se vería. Inicia
  sesión por la API. `reset_demo.py` antes y después; no correrlo mientras alguien grabe o ensaye con la app.
- El guion debe durar entre 9:30 y 10:00 y no pedir más de 2.6 palabras por segundo; si no, el build se detiene.
- Misma verificación que la otra versión: `out_capturas/verificacion.md` e imágenes en `out_capturas/diapositivas/`.
