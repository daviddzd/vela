# Instructivo: 20 frases por integrante (cuarto conjunto de evaluación de ORACLE-Voz)

**Objetivo.** Probar el triaje con frases que nadie escribió pensando en las reglas. Por eso:
**no abras** `config/emergency_rules.yaml`, `voice/` ni los otros CSV de `data/voice/` antes de terminar.

## Qué escribir
20 mensajes que un familiar o cuidador le mandaría al equipo de cuidado sobre una persona mayor
(«mi mamá», «don Chuy», «la señora»…). Inventados: **ningún dato real**.

- **7 de emergencia** (hay que llamar al 911 ya). Elige categorías distintas:
  dificultad grave para respirar · dolor fuerte en el pecho · pérdida de la conciencia · signos de embolia
  (cara chueca, habla rara, un lado débil) · convulsiones · sangrado abundante · caída con golpe o que no puede
  levantarse · confusión súbita grave · intención de hacerse daño.
- **7 urgentes** (el equipo debe atenderlo hoy, pero no es 911): fiebre, dolor moderado, vómito, no comió,
  caída leve sin lesión, herida que se ve mal, olvidó medicinas, presión algo alta, tristeza sin intención de
  hacerse daño…
- **6 de rutina** (sin problema de salud): horarios, confirmar visitas, pagos, cambios de domicilio, «todo bien».

## Cómo escribirlas
Como hablas tú y tu familia: coloquial, con rodeos, algunas sin acentos o con errores de dedo, algunas muy
cortas y otras largas que mezclan cosas (manda la parte más grave). Incluye 2 o 3 **casos difíciles**: algo que
suena alarmante pero no lo es («casi me da un infarto con el recibo») o una emergencia sin palabras obvias.

## Dónde
1. Copia `data/voice/team_phrases_template.csv` como `data/voice/team_phrases_<tus_iniciales>.csv`.
2. Una fila por frase: `phrase_id` = `TEAM-<iniciales>-01` … `-20`; `author` = tus iniciales; `text` entre
   comillas; `label` = `emergency` | `urgent` | `routine`; `category` = la categoría en inglés para emergencias
   (`severe_breathing`, `chest_pain`, `unconscious`, `stroke_signs`, `seizure`, `severe_bleeding`,
   `serious_fall`, `sudden_confusion`, `self_harm`) o `none`; `style` = `colloquial` | `typo` | `long_mixed` |
   `regional` | `hard_case` | `short`.
3. Haz commit del archivo **antes** de que alguien corra la evaluación (así queda claro que se etiquetó a ciegas).

Se evalúan después, todas juntas, como cuarto conjunto. **No se usan para ajustar reglas ni para entrenar.**
