# Plan de estudio de 4 días {#guia-plan}

**Todo el equipo defiende todo**: no nos dividimos por materias. Por eso los cuatro leemos lo mismo, en el mismo orden, y
cada día cerramos con una ronda de preguntas entre nosotros. Las páginas se cuentan solas al generar el libro.

| Día | Qué leer | Páginas | Al terminar el día, cada quien puede… |
|---|---|---|---|
| **1** | **Parte I · El proyecto**: @ref(cap-que-es), @ref(cap-recorrido), @ref(cap-arquitectura), @ref(cap-datos), @ref(cap-seguridad) | {{ paginas cap-que-es cap-operacion }} | explicar Enlaza en dos minutos, recorrerlo por rol, decir qué es {{ mod.llm_nombre }} y por qué {{ ops.public_url }} no es un hosting |
| **2** | **Parte II · Cómo funciona cada módulo**: operación, tiempo real, Panorama-AM, SIRAG-D, contingencia, Enlaza Voz, negocio y ética (@ref(cap-operacion) a @ref(cap-etica)) | {{ paginas cap-operacion cap-m-pp-doc }} | contar qué nos dijo la simulación, los dos niveles de la voz con sus falsas alarmas, y el escenario recomendado con su condición |
| **3** | **Parte III · Por materia**: @ref(cap-m-pp-doc) y las seis materias (@ref(cap-m-sie) a @ref(cap-m-pp)) | {{ paginas cap-m-pp-doc cap-bitacora }} | responder las 10 preguntas difíciles de cualquier materia, no solo de «la suya» |
| **4** | **Parte IV y Parte V** (@ref(cap-bitacora) a @ref(cap-planb)); después la **Guía rápida** (@ref(guia-tres-paginas), @ref(guia-numeros), @ref(guia-preguntas)) y al final el **guion del coloquio** (`docs/presentacion/guion_coloquio.pdf`, {{ pres.guion_paginas }} páginas) | {{ paginas cap-bitacora anx-usuarios }} + {{ paginas guia-tres-paginas guia-plan }} + {{ pres.guion_paginas }} | contar cómo se construyó (y responder «¿ustedes programaron esto?»), operar la demo, aplicar el plan B y decir su parte del guion sin leer |

**Cómo estudiar cada día**

1. Leer las secciones **«En una frase»** y **«Explicado sin tecnicismos»** de cada capítulo del día; luego el resto.
2. En **«Preguntas que te pueden hacer»**, tapar la respuesta y contestar en voz alta.
3. Al final del día, 15 minutos de ronda: cada quien hace dos preguntas difíciles a otro integrante, de cualquier tema.
4. Los números se aprenden de @ref(guia-numeros), no de memoria suelta: cada uno trae su fuente.

**El día 4 termina con un ensayo completo** del guion (`docs/presentacion/guion_coloquio.md`) con cronómetro, la demostración en
vivo por {{ ops.public_url }} y la ronda de 5 minutos de preguntas. Los anexos (usuarios, comandos, mapa del repositorio y
criterios) son de consulta: no hace falta leerlos completos.
