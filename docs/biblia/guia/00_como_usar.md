# Cómo usar esta biblia {#guia-como-usar}

**Para qué sirve.** Para que cualquier integrante del equipo pueda explicar y defender cualquier parte de Enlaza ante cualquier
profesor, aunque no la haya programado.

**Cómo está organizada.**

| Parte | Para qué | Cuándo leerla |
|---|---|---|
| Guía rápida | lo indispensable en pocas páginas | el día antes y una hora antes de la defensa |
| I · El proyecto | qué es, qué ve cada persona, arquitectura, datos, seguridad | todos, primero |
| II · Cómo funciona cada módulo | cada módulo por dentro | todo el equipo |
| III · Por materia | lo que pide el documento oficial, conceptos desde cero, guion de 2 minutos, 10 preguntas | todo el equipo: cada quien defiende todo |
| IV · Historia y decisiones | qué pasó, por qué se decidió así, cómo se construyó | todos (preguntas de «¿por qué?») |
| V · Operación práctica | preparar, encender, respaldar, presentar, plan B | quien opera la laptop |
| Anexos | glosario, usuarios, comandos, mapa del repositorio, criterios y referencias APA 7 | consulta |

**Cómo leer cada capítulo.** Todos tienen las mismas secciones: *En una frase* · *Explicado sin tecnicismos* · *Por qué lo
hicimos así* · *Cómo funciona por dentro* · *Dónde está en el código* · *Números clave* · *Limitaciones honestas* · *Preguntas
que te pueden hacer*. Si solo tienes cinco minutos, lee «En una frase» y las preguntas.

**Convenciones.**

- Un término en **verde con flecha** (por ejemplo, [[SaaS]]) está en el glosario; la flecha lleva a su definición.
- Una referencia como @ref(cap-seguridad) lleva al capítulo y dice su página.
- **Ningún número está escrito a mano**: cada cifra sale de un archivo del repositorio, de la base de datos o de un documento
  citado, y las tablas «Números clave» dicen de dónde. Si cambian los resultados, se regenera el libro y todo queda al día.
- Lo que dice **«supuesto»** es una decisión del equipo, no un dato medido. Lo que dice **«histórico»** es de una corrida anterior,
  citada con su documento.
- Lo que dice **«pendiente»** o **«confirmar con el profesor»** no está resuelto: no lo presentes como hecho.

**Cómo regenerarla.** `bash scripts/build_biblia.sh` (con `--capturas` para tomar de nuevo todas las pantallas). Las fuentes están
en `docs/biblia/`; el PDF no se sube a Git.
