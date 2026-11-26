# Criterios de aceptación y evidencia {#anx-criterios}

Los criterios A1–A13 de `docs/spec/10_plan_demo_y_criterios.md` y dónde está la evidencia de cada uno.

| # | Criterio | Evidencia | Estado |
|---|---|---|---|
| A1 | La semilla carga con los conteos esperados y 0 traslapes | `scripts/verify_db.py` («Todo correcto») | cumple |
| A2 | Sin institución la API ve 0 filas; INS-A no lee un paciente de INS-B (403 + bitácora) | `backend/tests/test_tenant_isolation.py`; hoy: {{ db.rls_patients_none }} sin institución | cumple |
| A3 | Baja/media se asigna sola en menos de 5 s; alta queda pendiente | `backend/tests/test_operations.py` | cumple |
| A4 | El tablero se actualiza sin recargar en menos de 2 s, también por Cloudflare | medición manual: {{ man.evento_tunel_s }} | cumple (medido una vez) |
| A5 | Sin consentimiento no se graba voz ni se ven datos de salud | `test_voice.py`, `test_privacy.py`, `test_patients_staff.py`; también con asentimiento «no» | cumple |
| A6 | 100 % de las frases de emergencia del conjunto de prueba terminan en emergencia | prueba interna: {{ voz.internal_test.sens }}; holdout a ciegas: {{ voz.holdout.sens }} | cumple en prueba interna; ver @ref(cap-voz) |
| A7 | La pantalla 911 aparece en menos de 3 s tras transcribir, sin esperar al LLM | flujo: la pantalla sale con el nivel; el reporte va en segundo plano | cumple (revisión manual) |
| A8 | El reporte no contiene diagnósticos (revisión de 20) | {{ voz.reports_clean }} de {{ voz.reports_reviewed }} sin frases prohibidas (filtro) | **falta la revisión humana** |
| A9 | SIRAG-D corre 4 × 3 × 30 con intervalos de confianza | {{ sim.runs_main }} corridas principales (5 políticas × 3 × {{ cfg.replications }}) | cumple |
| A10 | La contingencia del panel genera propuesta y nada cambia sin aprobación | capturas de @ref(cap-contingencia); `test_contingency.py` | cumple |
| A11 | Toda cifra visible tiene fuente o dice «supuesto» | tarjetas con fuente; `assumptions.csv`; este libro (cada número con su fuente) | cumple |
| A12 | No hay secretos en el repositorio | `.env` ignorado; solo la contraseña pública de demostración | revisar con `git log -p` antes de la defensa |
| A13 | Contraste AA y modo sencillo | `scripts/check_contrast.py`; Lighthouse ≥ 90 | contraste cumple; **Lighthouse: revisar a mano** |
